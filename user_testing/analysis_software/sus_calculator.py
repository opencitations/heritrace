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


class SUSCalculator:
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
        """Process all SUS files for a specific user type."""
        sus_dir = self.results_dir / user_type / "sus"
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
                    'user_type': user_type,
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
                
            stats[user_type] = {
                'count': len(scores),
                'mean': np.mean(scores),
                'std': np.std(scores, ddof=1) if len(scores) > 1 else 0,
                'median': np.median(scores),
                'min': np.min(scores),
                'max': np.max(scores),
                'scores': scores
            }
            
        return stats
    
    
    def create_visualizations(self, all_results: List[Dict]):
        """Generate visualizations for SUS scores."""
        if not all_results:
            print("No data to visualize")
            return

        df = pd.DataFrame(all_results)

        # Create figure with subplots (1x2): SUS boxplot + Summary
        # Use 16:9 aspect ratio to better utilize horizontal space
        fig = plt.figure(figsize=(12, 6.75))
        gs = fig.add_gridspec(1, 2, width_ratios=[1.5, 1], wspace=0.3, top=0.95, bottom=0.22)
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])

        # 1. Box plot by user type
        user_types = list(df['user_type'].unique())
        box_data = [df[df['user_type'] == ut]['sus_score'].values for ut in user_types]
        box_plot = ax1.boxplot(box_data, tick_labels=user_types, patch_artist=True,
                               medianprops=dict(color='darkblue', linewidth=2.5))
        ax1.set_title('SUS score distribution by user type')
        ax1.set_ylabel('SUS score')
        ax1.axhline(y=68, color='orange', linestyle='--', alpha=0.7, label='Average threshold')
        ax1.axhline(y=80.3, color='green', linestyle='--', alpha=0.7, label='Excellent threshold')
        # Add median to legend
        ax1.plot([], [], color='darkblue', linewidth=2.5, label='Median')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Color boxes
        base_colors = ['lightblue', 'lightcoral', 'lightgreen', 'wheat', 'plum', 'khaki']
        colors = (base_colors * ((len(user_types) // len(base_colors)) + 1))[: len(user_types)]
        for patch, color in zip(box_plot['boxes'], colors):
            patch.set_facecolor(color)

        # 2. Summary statistics table (text-based)
        ax2.axis('off')
        stats_lines = ["SUS statistics summary", ""]
        for user_type in user_types:
            user_data = df[df['user_type'] == user_type]['sus_score']
            q1 = user_data.quantile(0.25)
            q3 = user_data.quantile(0.75)
            median = user_data.median()
            min_val = user_data.min()
            max_val = user_data.max()

            stats_lines.append(f"{user_type.replace('_', ' ').title()}:")
            stats_lines.append(f"  Count: {len(user_data)}")
            stats_lines.append(f"  Mean SUS: {user_data.mean():.1f}")
            stats_lines.append(f"  Median: {median:.1f}")
            stats_lines.append(f"  Q1 (25th percentile): {q1:.1f}")
            stats_lines.append(f"  Q3 (75th percentile): {q3:.1f}")
            stats_lines.append(f"  Range: {min_val:.1f}-{max_val:.1f}")
            stats_lines.append("")
        stats_text = "\n".join(stats_lines)
        ax2.text(0.05, 0.95, stats_text, transform=ax2.transAxes, fontsize=10,
                 verticalalignment='top', fontfamily='monospace')

        # Add box plot legend explaining elements (positioned below the plot)
        legend_text = (
            "Box plot elements:\n"
            "• Box edges: 25th (Q1) and 75th (Q3) percentiles (interquartile range, IQR)\n"
            "• Blue line: Median (50th percentile)\n"
            "• Whiskers: Extend to the most extreme data point within 1.5×IQR from box edges\n"
            "• Circles: Outliers (values beyond 1.5×IQR from box edges)"
        )
        fig.text(0.5, 0.04, legend_text, ha='center', fontsize=10,
                 verticalalignment='bottom', multialignment='left')

        # Save visualization
        output_file = self.output_dir / "sus_visualizations.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Visualizations saved to: {output_file}")
        plt.close()
    
    def generate_reports(self) -> Dict:
        """Generate comprehensive SUS analysis reports."""
        all_results = []
        
        user_types = ['endusers', 'technicians']

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
        
        self.create_visualizations(all_results)
        
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