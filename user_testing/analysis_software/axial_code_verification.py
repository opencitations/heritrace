#!/usr/bin/env python3
"""
Axial Code Verification Tool

Verifies if all open codes have been properly considered in axial coding analysis.
Compares open coding files with axial coding files to identify missing codes.
"""

import json
from pathlib import Path
from typing import Dict, Set, Tuple


def load_open_codes(directory: str) -> Dict[str, Set[str]]:
    """Load all open codes from a directory."""
    codes_by_participant = {}
    directory_path = Path(directory)
    
    if not directory_path.exists():
        print(f"Error: Directory {directory} does not exist")
        return {}
    
    for file_path in directory_path.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                participant_id = data.get("participant_id", "unknown")
                codes = {code["code"] for code in data.get("codes", [])}
                codes_by_participant[participant_id] = codes
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return codes_by_participant


def load_axial_codes(file_path: str) -> Set[str]:
    """Load all codes referenced in axial coding file."""
    axial_codes = set()
    
    if not Path(file_path).exists():
        print(f"Error: File {file_path} does not exist")
        return axial_codes
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for category in data.get("categories", []):
                for code_entry in category.get("related_codes", []):
                    axial_codes.add(code_entry.get("code", ""))
                    
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    
    return axial_codes


def verify_coverage(open_codes_dir: str, axial_codes_file: str) -> Tuple[Set[str], Set[str]]:
    """Verify coverage of open codes in axial codes."""
    open_codes_by_participant = load_open_codes(open_codes_dir)
    axial_codes = load_axial_codes(axial_codes_file)
    
    all_open_codes = set()
    for participant_codes in open_codes_by_participant.values():
        all_open_codes.update(participant_codes)
    
    missing_codes = all_open_codes - axial_codes
    extra_codes = axial_codes - all_open_codes
    
    return missing_codes, extra_codes


def print_results(user_type: str, missing_codes: Set[str], extra_codes: Set[str], 
                 open_codes_dir: str, axial_codes_file: str):
    """Print verification results."""
    print(f"\n{'='*60}")
    print(f"AXIAL CODE VERIFICATION RESULTS - {user_type.upper()} USERS")
    print(f"{'='*60}")
    
    print(f"\nOpen codes directory: {open_codes_dir}")
    print(f"Axial codes file: {axial_codes_file}")
    
    if not missing_codes and not extra_codes:
        print(f"\nPERFECT COVERAGE: All open codes are properly included in axial coding.")
        return
    
    if missing_codes:
        print(f"\nMISSING CODES ({len(missing_codes)} codes not covered in axial coding):")
        for code in sorted(missing_codes):
            print(f"  - {code}")
    
    if extra_codes:
        print(f"\nEXTRA CODES ({len(extra_codes)} codes in axial coding but not in open coding):")
        for code in sorted(extra_codes):
            print(f"  - {code}")
    
    total_open_codes = len(load_open_codes(open_codes_dir))
    if total_open_codes > 0:
        coverage_percentage = ((total_open_codes - len(missing_codes)) / total_open_codes) * 100
        print(f"\nCoverage: {coverage_percentage:.1f}%")


def main():
    enduser_open_codes_dir = "../results/endusers/open_coding"
    enduser_axial_codes_file = "../results/endusers/end_user_axial_codes.json"
    
    technician_open_codes_dir = "../results/technicians/open_coding"
    technician_axial_codes_file = "../results/technicians/technician_axial_codes.json"
    
    missing_codes, extra_codes = verify_coverage(enduser_open_codes_dir, enduser_axial_codes_file)
    print_results("end_user", missing_codes, extra_codes, enduser_open_codes_dir, enduser_axial_codes_file)
    
    missing_codes, extra_codes = verify_coverage(technician_open_codes_dir, technician_axial_codes_file)
    print_results("technician", missing_codes, extra_codes, technician_open_codes_dir, technician_axial_codes_file)


if __name__ == "__main__":
    main()