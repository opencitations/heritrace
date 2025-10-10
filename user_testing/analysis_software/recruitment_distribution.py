#!/usr/bin/env python3
"""
Recruitment distribution analysis for HERITRACE user testing
Analyzes participant familiarity with HERITRACE and SHACL from written answers
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt


class RecruitmentAnalyzer:
    def __init__(self):
        script_dir = Path(__file__).resolve().parent
        self.results_dir = script_dir.parent / "results"
        self.output_dir = self.results_dir / "aggregated_analysis" / "recruitment"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse_checkbox_question(self, content: str, question_text: str) -> Optional[str]:
        """Extract the selected checkbox option for a given question.

        Returns the text of the selected option (marked with [X] or [x]).
        """
        question_pattern = re.escape(question_text) + r'\s*\n((?:- \[[ Xx]\].*\n?)+)'
        question_match = re.search(question_pattern, content, re.MULTILINE)

        if not question_match:
            return None

        options_text = question_match.group(1)

        checked_pattern = r'- \[[Xx]\]\s*(.+)'
        checked_match = re.search(checked_pattern, options_text)

        if checked_match:
            return checked_match.group(1).strip()

        return None

    def parse_enduser_file(self, file_path: Path) -> Optional[Dict]:
        """Extract HERITRACE familiarity from end user written answer file."""
        try:
            content = file_path.read_text()

            heritrace_answer = self.parse_checkbox_question(
                content,
                "Did you know HERITRACE before taking this test?"
            )

            if not heritrace_answer:
                print(f"Warning: could not parse HERITRACE question in {file_path}")
                return None

            return {
                'participant_id': file_path.stem.replace('_written_answer', ''),
                'user_type': 'endusers',
                'heritrace_familiarity': heritrace_answer,
                'file_path': str(file_path)
            }
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def parse_technician_file(self, file_path: Path) -> Optional[Dict]:
        """Extract SHACL and HERITRACE familiarity from technician written answer file."""
        try:
            content = file_path.read_text()

            shacl_answer = self.parse_checkbox_question(
                content,
                "Did you know SHACL before taking this test?"
            )

            heritrace_answer = self.parse_checkbox_question(
                content,
                "Did you know HERITRACE before taking this test?"
            )

            if not shacl_answer or not heritrace_answer:
                print(f"Warning: could not parse questions in {file_path}")
                return None

            return {
                'participant_id': file_path.stem.replace('_written_answer', ''),
                'user_type': 'technicians',
                'shacl_familiarity': shacl_answer,
                'heritrace_familiarity': heritrace_answer,
                'file_path': str(file_path)
            }
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def process_user_type(self, user_type: str) -> List[Dict]:
        """Process all written answer files for a specific user type."""
        written_answers_dir = self.results_dir / user_type / "written_answers"
        results = []

        if not written_answers_dir.exists():
            print(f"Warning: written answers directory not found: {written_answers_dir}")
            return results

        for answer_file in written_answers_dir.glob("*_written_answer.md"):
            if user_type == 'endusers':
                parsed = self.parse_enduser_file(answer_file)
            else:
                parsed = self.parse_technician_file(answer_file)

            if parsed:
                results.append(parsed)

        return results

    def categorize_response(self, response: str, question_type: str = 'heritrace') -> str:
        """Categorize responses into standardized levels."""
        response_lower = response.lower()

        if question_type == 'heritrace':
            if 'master' in response_lower:
                return 'Mastered'
            elif 'usage knowledge' in response_lower:
                return 'Usage knowledge'
            elif 'never' in response_lower:
                return 'No experience'
        elif question_type == 'shacl':
            if 'master' in response_lower or 'perfectly' in response_lower:
                return 'Mastered'
            elif 'working knowledge' in response_lower:
                return 'Working knowledge'
            elif 'not at all' in response_lower:
                return 'No experience'

        return 'Other'

    def create_distribution_chart(self, data: List[Dict], field: str, title: str,
                                  filename: str, colors: Optional[List[str]] = None):
        """Create a bar chart showing distribution of responses."""
        if not data:
            return

        responses = [self.categorize_response(d[field],
                                              'shacl' if 'shacl' in field else 'heritrace')
                    for d in data]

        unique_responses = list(set(responses))
        counts = {resp: responses.count(resp) for resp in unique_responses}

        order = ['No experience', 'Usage knowledge', 'Working knowledge', 'Mastered', 'Other']
        sorted_responses = [r for r in order if r in counts]
        sorted_counts = [counts[r] for r in sorted_responses]

        if not colors:
            colors = ['#d73027', '#fdae61', '#fee08b', '#1b7837', '#999999']
        colors = colors[:len(sorted_responses)]

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(range(len(sorted_responses)), sorted_counts, color=colors,
                      edgecolor='white', linewidth=1.5)

        ax.set_xticks(range(len(sorted_responses)))
        ax.set_xticklabels(sorted_responses, rotation=15, ha='right')
        ax.set_ylabel('Number of participants')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='y')

        for bar, count in zip(bars, sorted_counts):
            height = bar.get_height()
            percentage = (count / len(data)) * 100
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{count}\n({percentage:.1f}%)',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')

        total_text = f'Total participants: {len(data)}'
        ax.text(0.98, 0.98, total_text, transform=ax.transAxes,
               ha='right', va='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        output_file = self.output_dir / filename
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_file}")
        plt.close()

    def create_combined_visualization(self, enduser_data: List[Dict],
                                     technician_data: List[Dict]):
        """Create a combined visualization showing all distributions."""
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.3)

        colors_heritrace = ['#d73027', '#fdae61', '#1b7837']
        colors_shacl = ['#4575b4', '#fee08b', '#1b7837']

        def plot_distribution(ax, data, field, title, colors, question_type):
            if not data:
                return

            responses = [self.categorize_response(d[field], question_type) for d in data]
            unique_responses = list(set(responses))
            counts = {resp: responses.count(resp) for resp in unique_responses}

            order = ['No experience', 'Usage knowledge', 'Working knowledge', 'Mastered', 'Other']
            sorted_responses = [r for r in order if r in counts]
            sorted_counts = [counts[r] for r in sorted_responses]
            plot_colors = colors[:len(sorted_responses)]

            bars = ax.bar(range(len(sorted_responses)), sorted_counts, color=plot_colors,
                         edgecolor='white', linewidth=1.5)
            ax.set_xticks(range(len(sorted_responses)))
            ax.set_xticklabels(sorted_responses, rotation=15, ha='right')
            ax.set_ylabel('Number of participants')
            ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
            ax.grid(True, alpha=0.3, axis='y')

            for bar, count in zip(bars, sorted_counts):
                height = bar.get_height()
                percentage = (count / len(data)) * 100
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{count}\n({percentage:.1f}%)',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')

            ax.text(0.98, 0.98, f'n = {len(data)}', transform=ax.transAxes,
                   ha='right', va='top', fontsize=9,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax1 = fig.add_subplot(gs[0, :])
        plot_distribution(ax1, enduser_data, 'heritrace_familiarity',
                         'End users: HERITRACE familiarity', colors_heritrace, 'heritrace')

        ax2 = fig.add_subplot(gs[1, 0])
        plot_distribution(ax2, technician_data, 'heritrace_familiarity',
                         'Technicians: HERITRACE familiarity', colors_heritrace, 'heritrace')

        ax3 = fig.add_subplot(gs[1, 1])
        plot_distribution(ax3, technician_data, 'shacl_familiarity',
                         'Technicians: SHACL familiarity', colors_shacl, 'shacl')

        fig.suptitle('Participant recruitment distribution analysis',
                    fontsize=16, fontweight='bold', y=0.995)

        output_file = self.output_dir / "recruitment_distribution_combined.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_file}")
        plt.close()

    def generate_summary_stats(self, all_data: List[Dict]) -> Dict:
        """Generate summary statistics for recruitment distribution."""
        stats = {
            'total_participants': len(all_data),
            'by_user_type': {},
            'heritrace_distribution': {},
            'shacl_distribution': {}
        }

        endusers = [d for d in all_data if d['user_type'] == 'endusers']
        technicians = [d for d in all_data if d['user_type'] == 'technicians']

        stats['by_user_type']['endusers'] = len(endusers)
        stats['by_user_type']['technicians'] = len(technicians)

        all_heritrace = [self.categorize_response(d['heritrace_familiarity'], 'heritrace')
                        for d in all_data]
        for resp in set(all_heritrace):
            stats['heritrace_distribution'][resp] = all_heritrace.count(resp)

        tech_shacl = [self.categorize_response(d['shacl_familiarity'], 'shacl')
                     for d in technicians]
        for resp in set(tech_shacl):
            stats['shacl_distribution'][resp] = tech_shacl.count(resp)

        return stats

    def generate_report(self) -> Dict:
        """Generate comprehensive recruitment distribution analysis."""
        enduser_data = self.process_user_type('endusers')
        technician_data = self.process_user_type('technicians')

        all_data = enduser_data + technician_data

        if not all_data:
            print("No recruitment data found to process")
            return {}

        summary_stats = self.generate_summary_stats(all_data)

        detailed_report = {
            'participants': all_data,
            'summary_statistics': summary_stats,
            'metadata': {
                'total_participants': len(all_data),
                'endusers_count': len(enduser_data),
                'technicians_count': len(technician_data)
            }
        }

        report_file = self.output_dir / "recruitment_distribution.json"
        with open(report_file, 'w') as f:
            json.dump(detailed_report, f, indent=2)
        print(f"Report saved to: {report_file}")

        self.create_combined_visualization(enduser_data, technician_data)

        return detailed_report


def main():
    """Main execution function"""
    analyzer = RecruitmentAnalyzer()
    report = analyzer.generate_report()

    if report:
        print("\nRecruitment distribution analysis complete!")
        stats = report['summary_statistics']
        print(f"Total participants analyzed: {stats['total_participants']}")
        print(f"\nBy user type:")
        for user_type, count in stats['by_user_type'].items():
            print(f"  {user_type}: {count}")

        print(f"\nHERITRACE familiarity distribution:")
        for level, count in stats['heritrace_distribution'].items():
            print(f"  {level}: {count}")

        print(f"\nSHACL familiarity distribution (technicians only):")
        for level, count in stats['shacl_distribution'].items():
            print(f"  {level}: {count}")


if __name__ == "__main__":
    main()
