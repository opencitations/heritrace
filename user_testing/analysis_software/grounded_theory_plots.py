import json
import warnings
from pathlib import Path
from typing import Dict

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

from plot_utils import SENTIMENT_COLORS, SENTIMENT_HATCHES

warnings.filterwarnings('ignore')


def load_axial_codes(user_type: str, repo_root: Path) -> Dict:
    """Load axial codes JSON for a given user type."""
    folder = 'endusers' if user_type == 'end_user' else 'technicians'
    file_path = repo_root / 'results' / folder / f'{user_type}_axial_codes.json'

    if not file_path.exists():
        raise FileNotFoundError(f"Axial codes file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def humanize_user_type(user_type: str) -> str:
    """Convert user_type to human-readable format."""
    return user_type.replace('_', ' ').title()


def create_horizontal_bar_chart(user_type: str, repo_root: Path, output_dir: Path):
    """
    Create a horizontal bar chart showing axial categories ordered by frequency,
    with color encoding for sentiment.
    """
    axial = load_axial_codes(user_type, repo_root)
    categories = axial['categories']

    # Extract data
    cat_names = []
    frequencies = []
    sentiments = []

    for cat in categories:
        sentiment = cat['overall_sentiment']
        cat_names.append(cat['category_name'])
        frequencies.append(int(cat['frequency']))
        sentiments.append(sentiment)

    # Create DataFrame and sort by frequency
    df = pd.DataFrame({
        'category': cat_names,
        'frequency': frequencies,
        'sentiment': sentiments
    })
    df = df.sort_values('frequency', ascending=True)  # Ascending for horizontal bars

    # Create plot
    fig, ax = plt.subplots(figsize=(10, max(6, len(df) * 0.4)))

    # Map sentiments to colors and hatch patterns
    colors = [SENTIMENT_COLORS[s] for s in df['sentiment']]
    hatches = [SENTIMENT_HATCHES[s] for s in df['sentiment']]

    # Create horizontal bars with hatch patterns for black & white readability
    bars = ax.barh(df['category'], df['frequency'], color=colors, edgecolor='black', linewidth=0.8)

    # Apply hatch patterns to each bar
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)

    # Add frequency labels at the end of each bar
    for i, (freq, cat) in enumerate(zip(df['frequency'], df['category'])):
        ax.text(freq + max(df['frequency']) * 0.01, i, f' {freq}',
                va='center', ha='left', fontsize=9, fontweight='bold')

    # Set x-axis limit to accommodate the labels
    ax.set_xlim(0, max(df['frequency']) * 1.15)

    ax.set_xlabel('Frequency', fontsize=12, fontweight='bold')
    ax.set_title(f'Axial categories by frequency — {humanize_user_type(user_type)}',
                fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    # Create legend with hatch patterns for black & white readability
    legend_elements = [
        mpatches.Patch(facecolor=SENTIMENT_COLORS['positive'], edgecolor='black',
                      hatch=SENTIMENT_HATCHES['positive'], label='Positive'),
        mpatches.Patch(facecolor=SENTIMENT_COLORS['negative'], edgecolor='black',
                      hatch=SENTIMENT_HATCHES['negative'], label='Negative'),
    ]

    ax.legend(handles=legend_elements, loc='lower right', frameon=True, fontsize=12,
             handlelength=2.5, handleheight=1.5)

    plt.tight_layout()
    output_file = output_dir / f'{user_type}_axial_categories.png'
    fig.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {output_file}")


def main():
    """Main entry point for generating grounded theory visualizations."""
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    output_dir = repo_root / 'results' / 'aggregated_analysis' / 'grounded_theory'
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating grounded theory visualizations...")
    print("=" * 60)

    user_types = ['end_user', 'technician']

    for user_type in user_types:
        print(f"\nProcessing {user_type}...")
        print("-" * 60)

        try:
            create_horizontal_bar_chart(user_type, repo_root, output_dir)
            print(f"✓ Completed visualization for {user_type}")

        except Exception as e:
            print(f"✗ Error processing {user_type}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"All visualizations saved to: {output_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
