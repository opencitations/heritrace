#!/usr/bin/env python3
"""
Selective Code Verification Tool

Verifies if all axial codes have been properly considered in selective coding analysis.
Compares axial coding files with selective coding files to identify missing categories.
"""

import json
from pathlib import Path
from typing import Dict, Set, Tuple
from datetime import datetime


def load_axial_categories(file_path: str) -> Dict[str, int]:
    """Load all categories from axial coding file."""
    categories = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

        for category in data["categories"]:
            category_name = category["category_name"]
            frequency = category["frequency"]
            # Convert frequency to integer if it's a string
            if isinstance(frequency, str) and frequency.isdigit():
                frequency = int(frequency)
            elif not isinstance(frequency, int):
                frequency = 0
            categories[category_name] = frequency

    return categories


def load_selective_categories(file_path: str) -> Tuple[Set[str], Dict[str, int]]:
    """Load all axial codes referenced in selective coding file and their frequencies."""
    selective_categories = set()
    selective_frequencies = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

        # Only add axial codes included in supporting categories
        # (NOT the supporting category names themselves, as those are theoretical groupings)
        for category in data["supporting_categories"]:
            category_name = category["category"]

            # Store frequency for this supporting category
            frequency = category["frequency"]
            if isinstance(frequency, str) and frequency.isdigit():
                frequency = int(frequency)
            elif not isinstance(frequency, int):
                frequency = 0
            selective_frequencies[category_name] = frequency

            # Add only the axial codes that are included in this supporting category
            for axial_code in category["axial_codes_included"]:
                selective_categories.add(axial_code)

    return selective_categories, selective_frequencies


def verify_coverage(axial_codes_file: str, selective_codes_file: str) -> Tuple[Set[str], Set[str], float, Dict[str, Tuple[int, int]]]:
    """Verify coverage of axial codes in selective codes and check frequency accuracy."""
    axial_categories = load_axial_categories(axial_codes_file)
    selective_categories, selective_frequencies = load_selective_categories(selective_codes_file)

    axial_category_names = set(axial_categories.keys())

    missing_categories = axial_category_names - selective_categories
    extra_categories = selective_categories - axial_category_names

    total_axial = len(axial_category_names)
    covered = len(axial_category_names - missing_categories)
    coverage_percentage = (covered / total_axial * 100) if total_axial > 0 else 0.0

    # Check frequency mismatches by reading the selective codes file
    frequency_mismatches = {}

    with open(selective_codes_file, 'r', encoding='utf-8') as f:
        selective_data = json.load(f)

    for supporting_cat in selective_data["supporting_categories"]:
        cat_name = supporting_cat["category"]
        selective_freq = supporting_cat["frequency"]
        axial_codes_included = supporting_cat["axial_codes_included"]

        # Calculate expected frequency by summing axial category frequencies
        expected_freq = sum(axial_categories[axial_code] for axial_code in axial_codes_included)

        if selective_freq != expected_freq:
            frequency_mismatches[cat_name] = (expected_freq, selective_freq)

    return missing_categories, extra_categories, coverage_percentage, frequency_mismatches


def print_results(user_type: str, missing_categories: Set[str], extra_categories: Set[str],
                 coverage_percentage: float, frequency_mismatches: Dict[str, Tuple[int, int]],
                 axial_codes_file: str, selective_codes_file: str):
    """Print verification results."""
    print(f"\n{'='*60}")
    print(f"SELECTIVE CODE VERIFICATION RESULTS - {user_type.upper()} USERS")
    print(f"{'='*60}")

    print(f"\nAxial codes file: {axial_codes_file}")
    print(f"Selective codes file: {selective_codes_file}")

    print(f"\nCoverage: {coverage_percentage:.1f}%")

    if not missing_categories and not extra_categories and not frequency_mismatches:
        print(f"\nPERFECT INTEGRATION: All axial categories are properly integrated in selective coding with correct frequencies.")
        return

    if missing_categories:
        print(f"\nMISSING CATEGORIES ({len(missing_categories)} categories not integrated in selective coding):")
        for category in sorted(missing_categories):
            print(f"  - {category}")

    if extra_categories:
        print(f"\nEXTRA CATEGORIES ({len(extra_categories)} categories in selective coding but not in axial coding):")
        for category in sorted(extra_categories):
            print(f"  - {category}")

    if frequency_mismatches:
        print(f"\nFREQUENCY MISMATCHES ({len(frequency_mismatches)} categories with incorrect frequency counts):")
        for category, (expected, actual) in sorted(frequency_mismatches.items()):
            print(f"  - {category}")
            print(f"    Expected: {expected} (sum of axial codes)")
            print(f"    Actual: {actual} (in selective codes)")
            print(f"    Difference: {actual - expected:+d}")


def generate_verification_report(user_type: str, missing_categories: Set[str], 
                               extra_categories: Set[str], coverage_percentage: float) -> Dict:
    """Generate verification report for potential integration into selective codes file."""
    return {
        "total_axial_categories": len(load_axial_categories(get_axial_file(user_type))),
        "categories_integrated": len(load_axial_categories(get_axial_file(user_type))) - len(missing_categories),
        "coverage_percentage": round(coverage_percentage, 1),
        "missing_categories": sorted(list(missing_categories)),
        "verification_timestamp": datetime.now().isoformat()
    }


def get_axial_file(user_type: str) -> str:
    """Get axial codes file path for user type."""
    if user_type == "end_user":
        return "../results/endusers/end_user_axial_codes.json"
    else:
        return "../results/technicians/technician_axial_codes.json"


def get_selective_file(user_type: str) -> str:
    """Get selective codes file path for user type."""
    if user_type == "end_user":
        return "../results/endusers/end_user_selective_codes.json"
    else:
        return "../results/technicians/technician_selective_codes.json"


def main():
    """Main verification function."""
    user_types = ["end_user", "technician"]

    for user_type in user_types:
        axial_file = get_axial_file(user_type)
        selective_file = get_selective_file(user_type)

        if not Path(axial_file).exists():
            print(f"\nSkipping {user_type}: Axial codes file not found: {axial_file}")
            continue

        if not Path(selective_file).exists():
            print(f"\nSkipping {user_type}: Selective codes file not found: {selective_file}")
            continue

        missing_categories, extra_categories, coverage_percentage, frequency_mismatches = verify_coverage(
            axial_file, selective_file
        )

        print_results(user_type, missing_categories, extra_categories,
                     coverage_percentage, frequency_mismatches, axial_file, selective_file)

        report = generate_verification_report(user_type, missing_categories,
                                            extra_categories, coverage_percentage)

        print(f"\nVerification Report for {user_type}:")
        print(f"  Total axial categories: {report['total_axial_categories']}")
        print(f"  Categories integrated: {report['categories_integrated']}")
        print(f"  Coverage percentage: {report['coverage_percentage']}%")
        if report['missing_categories']:
            print(f"  Missing categories: {len(report['missing_categories'])}")
        if frequency_mismatches:
            print(f"  Frequency mismatches: {len(frequency_mismatches)}")


if __name__ == "__main__":
    main()