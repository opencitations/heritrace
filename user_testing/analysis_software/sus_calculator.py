#!/usr/bin/env python3
"""
SUS Calculator for HERITRACE User Testing Analysis
Processes SUS questionnaire files and generates scores and reports
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from stats_utils import calculate_mean_confidence_interval, get_boxplot_legend_text


class SUSCalculator:
    # Map normalized user types to directory names
    USER_TYPE_TO_DIR = {
        'end_user': 'endusers',
        'technician': 'technicians'
    }

    def __init__(self, results_dir: str = "../results"):
        self.results_dir = Path(results_dir)
        self.output_dir = self.results_dir / "aggregated_analysis" / "sus"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def parse_sus_file(self, file_path: Path) -> Optional[Dict]:
        """Extract SUS ratings (1–5) from a markdown file.

        Returns None if the file cannot be parsed into exactly 10 ratings.
        """
        try:
            content = file_path.read_text()
            ratings = []
            
            rating_pattern = r"Your rating:\s*([1-5])"
            matches = re.findall(rating_pattern, content)
            
            if len(matches) == 11:
                # Remove the first match which is the example
                matches = matches[1:]
            
            if len(matches) != 10:
                print(f"Warning: Found {len(matches)} ratings in {file_path}, expected 10")
                return None
                
            ratings = [int(match) for match in matches]
            if any(r < 1 or r > 5 for r in ratings):
                print(f"Warning: Out-of-range rating found in {file_path}")
                return None
            
            return {
                'participant_id': file_path.stem.replace('_sus', ''),
                'ratings': ratings,
                'file_path': str(file_path)
            }
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def calculate_sus_score(self, ratings: List[int]) -> float:
        """Calculate SUS score using standard formula"""
        if len(ratings) != 10:
            raise ValueError(f"Expected 10 ratings, got {len(ratings)}")
            
        score = 0
        for i, rating in enumerate(ratings):
            if i % 2 == 0:  # Odd items (1,3,5,7,9) - zero-indexed
                score += rating - 1
            else:  # Even items (2,4,6,8,10)
                score += 5 - rating
                
        return score * 2.5
    
    
    def process_user_type(self, user_type: str) -> List[Dict]:
        """Process all SUS files for a specific user type.

        Args:
            user_type: Normalized user type ('end_user' or 'technician')
        """
        # Map normalized user type to directory name
        dir_name = self.USER_TYPE_TO_DIR[user_type]
        sus_dir = self.results_dir / dir_name / "sus"
        results = []

        if not sus_dir.exists():
            print(f"Warning: SUS directory not found: {sus_dir}")
            return results

        for sus_file in sus_dir.glob("*_sus.md"):
            parsed = self.parse_sus_file(sus_file)
            if parsed:
                score = self.calculate_sus_score(parsed['ratings'])
                results.append({
                    'participant_id': parsed['participant_id'],
                    'user_type': user_type,  # Use normalized name in output
                    'ratings': parsed['ratings'],
                    'sus_score': score,
                    'file_path': parsed['file_path']
                })

        return results
    
    def generate_aggregated_stats(self, scores_by_type: Dict[str, List[float]]) -> Dict:
        """Generate aggregated statistics by user type for primary SUS scores."""
        stats = {}

        for user_type, scores in scores_by_type.items():
            if not scores:
                continue

            # Calculate 95% confidence interval for mean
            mean_val, ci_lower, ci_upper = calculate_mean_confidence_interval(np.array(scores))

            stats[user_type] = {
                'count': len(scores),
                'mean': mean_val,
                'std': np.std(scores, ddof=1) if len(scores) > 1 else 0,
                'median': float(np.median(scores)),
                'min': float(np.min(scores)),
                'max': float(np.max(scores)),
                'ci_95_lower': ci_lower,
                'ci_95_upper': ci_upper,
                'scores': scores
            }

        return stats
    
    
    def create_visualizations(self, all_results: List[Dict], aggregated_stats: Dict):
        """Generate visualizations for SUS scores.

        Args:
            all_results: List of individual participant results
            aggregated_stats: Pre-computed aggregated statistics including CIs
        """
        if not all_results:
            print("No data to visualize")
            return

        df = pd.DataFrame(all_results)

        # Create figure with subplots (1x2): SUS boxplot + Summary
        # Compact layout with reduced dimensions
        fig = plt.figure(figsize=(10, 5.5))
        gs = fig.add_gridspec(1, 2, width_ratios=[1.5, 1], wspace=0.3, top=0.95, bottom=0.10)
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])

        # 1. Box plot by user type
        user_types = list(df['user_type'].unique())
        box_data = [df[df['user_type'] == ut]['sus_score'].values for ut in user_types]

        # Map user types to proper labels
        user_type_labels = []
        for ut in user_types:
            if 'enduser' in ut.lower():
                user_type_labels.append('End user')
            elif 'technician' in ut.lower():
                user_type_labels.append('Technician')
            else:
                user_type_labels.append(ut.replace('_', ' ').capitalize())

        box_plot = ax1.boxplot(box_data, tick_labels=user_type_labels, patch_artist=True,
                               showmeans=True, meanline=False,
                               medianprops=dict(color='darkblue', linewidth=2.5),
                               meanprops=dict(marker='D', markerfacecolor='red',
                                            markeredgecolor='black', markersize=6))
        ax1.set_title('SUS score distribution by user type')
        ax1.set_ylabel('SUS score')
        ax1.axhline(y=68, color='orange', linestyle='--', alpha=0.7, label='Average threshold')
        ax1.axhline(y=80.3, color='green', linestyle='--', alpha=0.7, label='Excellent threshold')

        # Use pre-computed 95% CI from aggregated statistics
        means = []
        ci_lowers = []
        ci_uppers = []
        for ut in user_types:
            ut_stats = aggregated_stats[ut]
            means.append(ut_stats['mean'])
            ci_lowers.append(ut_stats['ci_95_lower'])
            ci_uppers.append(ut_stats['ci_95_upper'])

        # Add confidence interval error bars
        x_positions = np.arange(1, len(means) + 1)
        ci_errors = [np.array(means) - np.array(ci_lowers),
                     np.array(ci_uppers) - np.array(means)]
        ax1.errorbar(x_positions, means, yerr=ci_errors,
                    fmt='none', ecolor='darkgreen', capsize=5, capthick=2,
                    linewidth=2, alpha=0.8, label='95% CI')

        # Updated legend with all elements
        ax1.plot([], [], color='darkblue', linewidth=2.5, label='Median')
        ax1.plot([], [], marker='D', color='red', linestyle='None',
                markeredgecolor='black', markersize=6, label='Mean')
        ax1.plot([], [], marker='o', markerfacecolor='none', markeredgecolor='black',
                linestyle='None', markersize=5, label='Outliers')
        # Extend Y-axis to create space for legend at bottom-right
        ax1.set_ylim(bottom=50)
        # Position legend in lower right with padding
        ax1.legend(loc='lower right', frameon=True, fontsize=9)
        ax1.grid(True, alpha=0.3)

        # Color boxes (consistent with task duration plots)
        user_type_colors = {
            'end_user': 'lightblue',
            'technician': 'lightcoral'
        }
        for patch, user_type in zip(box_plot['boxes'], user_types):
            color = user_type_colors[user_type]
            patch.set_facecolor(color)

        # 2. Summary statistics table (text-based) with box plot elements below
        ax2.axis('off')
        stats_lines = ["SUS statistics summary", ""]
        for user_type in user_types:
            user_data = df[df['user_type'] == user_type]['sus_score']
            q1 = user_data.quantile(0.25)
            q3 = user_data.quantile(0.75)
            median = user_data.median()
            min_val = user_data.min()
            max_val = user_data.max()

            # Map user types to proper labels
            if 'enduser' in user_type.lower():
                user_type_label = 'End user'
            elif 'technician' in user_type.lower():
                user_type_label = 'Technician'
            else:
                user_type_label = user_type.replace('_', ' ').capitalize()
            stats_lines.append(f"{user_type_label}:")
            stats_lines.append(f"  Count: {len(user_data)}")
            stats_lines.append(f"  Mean SUS: {user_data.mean():.1f}")
            stats_lines.append(f"  Median: {median:.1f}")
            stats_lines.append(f"  Q1 (25th percentile): {q1:.1f}")
            stats_lines.append(f"  Q3 (75th percentile): {q3:.1f}")
            stats_lines.append(f"  Range: {min_val:.1f}-{max_val:.1f}")
            stats_lines.append("")

        # Add box plot legend directly after statistics
        stats_lines.append("")
        legend_text = get_boxplot_legend_text()
        stats_lines.extend(legend_text.split("\n"))

        stats_text = "\n".join(stats_lines)
        ax2.text(0.05, 0.95, stats_text, transform=ax2.transAxes, fontsize=10,
                 verticalalignment='top', fontfamily='monospace')

        # Save visualization
        output_file = self.output_dir / "sus_visualizations.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualizations saved to: {output_file}")
        plt.close()
    
    def generate_reports(self) -> Dict:
        """Generate comprehensive SUS analysis reports."""
        all_results = []

        # Use normalized user type names
        user_types = ['end_user', 'technician']

        for user_type in user_types:
            results = self.process_user_type(user_type)
            all_results.extend(results)
            
        if not all_results:
            print("No SUS data found to process")
            return {}
            
        scores_by_type = {}
        for result in all_results:
            user_type = result['user_type']
            if user_type not in scores_by_type:
                scores_by_type[user_type] = []
            scores_by_type[user_type].append(result['sus_score'])
            
        aggregated_stats = self.generate_aggregated_stats(scores_by_type)

        individual_scores = {
            'participants': all_results,
            'metadata': {
                'total_participants': len(all_results),
                'user_types': list(scores_by_type.keys()),
                'analysis_date': pd.Timestamp.now().isoformat()
            }
        }

        aggregated_report = {
            'summary_statistics': aggregated_stats,
            'benchmarking': {
                'participants_below_average': len([r for r in all_results if r['sus_score'] < 68]),
                'participants_above_average': len([r for r in all_results if 68 <= r['sus_score'] < 80.3]),
                'participants_excellent': len([r for r in all_results if r['sus_score'] >= 80.3])
            },
            'metadata': {
                'analysis_date': pd.Timestamp.now().isoformat(),
                'benchmark_thresholds': {
                    'below_average': '< 68',
                    'above_average': '68-80.3',
                    'excellent': '>= 80.3'
                }
            }
        }
        
        individual_file = self.output_dir / "sus_individual_scores.json"
        with open(individual_file, 'w') as f:
            json.dump(individual_scores, f, indent=2)
        print(f"Individual scores saved to: {individual_file}")
        
        aggregated_file = self.output_dir / "sus_aggregated_report.json"
        with open(aggregated_file, 'w') as f:
            json.dump(aggregated_report, f, indent=2)
        print(f"Aggregated report saved to: {aggregated_file}")

        self.create_visualizations(all_results, aggregated_stats)
        
        return {
            'individual_scores': individual_scores,
            'aggregated_report': aggregated_report,
            'all_results': all_results
        }


def main():
    """Main execution function"""
    calculator = SUSCalculator()
    reports = calculator.generate_reports()
    
    if reports:
        print("\nSUS Analysis Complete!")
        print(f"Total participants analyzed: {len(reports['all_results'])}")

        for user_type, stats in reports['aggregated_report']['summary_statistics'].items():
            print(f"\n{user_type.replace('_', ' ').title()} (n={stats['count']}):")
            print(f"  Mean SUS score: {stats['mean']:.1f}")
            print(f"  Median SUS score: {stats['median']:.1f}")

        benchmarking = reports['aggregated_report']['benchmarking']
        print(f"\nBenchmarking results:")
        print(f"  Below average (<68): {benchmarking['participants_below_average']} participants")
        print(f"  Above average (68-80.3): {benchmarking['participants_above_average']} participants")
        print(f"  Excellent (≥80.3): {benchmarking['participants_excellent']} participants")


if __name__ == "__main__":
    main()