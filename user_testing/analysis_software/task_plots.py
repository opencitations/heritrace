import json
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
import numpy as np
import pandas as pd

from stats_utils import get_boxplot_legend_text


def load_duration_statistics(repo_root: Path) -> dict:
    """Load pre-computed duration statistics including confidence intervals."""
    json_path = repo_root / "results" / "aggregated_analysis" / "tasks" / "task_metrics.json"
    if not json_path.exists():
        return {}
    with open(json_path, "r") as f:
        data = json.load(f)
    return data["duration_statistics"]


def load_rows(repo_root: Path) -> pd.DataFrame:
    json_path = repo_root / "results" / "aggregated_analysis" / "tasks" / "task_metrics.json"
    if not json_path.exists():
        return pd.DataFrame()
    with open(json_path, "r") as f:
        data = json.load(f)
    rows = data["rows"]
    df = pd.DataFrame(rows)
    # Attach desired order per user type if present in metadata
    metadata = data["metadata"]
    order_by_user_type = metadata["task_order_by_user_type"]
    if not df.empty and order_by_user_type:
        def order_index(row):
            desired = order_by_user_type[str(row['user_type'])]
            try:
                return desired.index(row['task_key'])
            except Exception:
                return 10_000
        df['__task_order_idx'] = df.apply(order_index, axis=1)
    return df


def _humanize_text(value: str) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    # Use sentence case: only first letter capitalized
    text = str(value).replace("_", " ").strip()
    return text.capitalize() if text else ""


def _humanize_user_type(user_type: str) -> str:
    return _humanize_text(user_type)


def _task_key_to_label_map(df: pd.DataFrame) -> dict:
    if df.empty or 'task_key' not in df.columns:
        return {}
    unique_keys = (
        df['task_key']
          .dropna()
          .astype(str)
          .unique()
          .tolist()
    )
    return {k: _humanize_text(k) for k in unique_keys}


def plot_success_rates(df: pd.DataFrame, output_dir: Path):
    if df.empty:
        return
    task_label_map = _task_key_to_label_map(df)

    status_colors = {
        'complete': '#1b7837',
        'partial': '#fdae61',
        'success_timeout': '#4575b4',
        'failed_misunderstanding': '#d73027',
        'failed_bug': '#7b3294'
    }

    status_hatches = {
        'complete': '',
        'partial': '///',
        'success_timeout': '|||',
        'failed_misunderstanding': 'xxx',
        'failed_bug': '\\\\\\'
    }

    status_labels = {
        'complete': 'Complete',
        'partial': 'Partial',
        'success_timeout': 'Success: Timeout',
        'failed_misunderstanding': 'Failed: Misunderstanding',
        'failed_bug': 'Failed: Bug'
    }

    # Compute status counts by user_type and task_key
    group_cols = ["user_type", "task_key"]

    def _status_percentages(g: pd.DataFrame) -> pd.Series:
        status_lower = g['status'].astype(str).str.lower()
        total = len(g)
        if total == 0:
            return pd.Series({
                'complete': 0.0,
                'partial': 0.0,
                'success_timeout': 0.0,
                'failed_misunderstanding': 0.0,
                'failed_bug': 0.0
            })
        return pd.Series({
            'complete': (status_lower == 'complete').sum() / total * 100,
            'partial': (status_lower == 'partial').sum() / total * 100,
            'success_timeout': (status_lower == 'success_timeout').sum() / total * 100,
            'failed_misunderstanding': (status_lower == 'failed_misunderstanding').sum() / total * 100,
            'failed_bug': (status_lower == 'failed_bug').sum() / total * 100
        })

    rates = df.groupby(group_cols, group_keys=False).apply(_status_percentages, include_groups=False).reset_index()

    # If an order index is available, carry it for sorting within each user_type
    if "__task_order_idx" in df.columns:
        order_idx = df.groupby(group_cols)['__task_order_idx'].min().reset_index(name='order_idx')
        rates = rates.merge(order_idx, on=group_cols, how='left')

    user_types = sorted(rates['user_type'].unique().tolist())
    n = len(user_types)
    fig, axs = plt.subplots(1, n, figsize=(6 * n, 6), squeeze=False)

    for i, ut in enumerate(user_types):
        ax = axs[0, i]
        sub = rates[rates['user_type'] == ut].copy()

        if 'order_idx' in sub.columns:
            sub.sort_values(['order_idx', 'task_key'], inplace=True)
        else:
            sub.sort_values('task_key', inplace=True)

        labels = [task_label_map[k] for k in sub['task_key'].tolist()]
        x = np.arange(len(sub))

        # Create stacked bars
        status_order = ['complete', 'partial', 'success_timeout', 'failed_misunderstanding', 'failed_bug']
        bottom = np.zeros(len(sub))

        for status in status_order:
            values = sub[status].values
            bars = ax.bar(x, values, bottom=bottom,
                         color=status_colors[status],
                         label=status_labels[status],
                         edgecolor='black', linewidth=1.0,
                         hatch=status_hatches[status])

            # Set hatch color to be less intrusive
            for bar in bars:
                bar.set_edgecolor('black')

            # Add percentage labels for segments >= 5%
            for j, val in enumerate(values):
                if val >= 5.0:
                    y_pos = bottom[j] + val / 2
                    # Use white text with black outline for better visibility
                    ax.text(j, y_pos, f'{val:.0f}%',
                           ha='center', va='center',
                           fontsize=9, fontweight='bold',
                           color='white',
                           path_effects=[pe.withStroke(linewidth=2, foreground='black')])

            bottom += values

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha='right')
        ax.set_ylim(0, 100)
        ax.set_ylabel('Completion Status (%)')
        ax.set_title(f'Task Completion Distribution — {_humanize_user_type(ut)}')
        ax.grid(True, alpha=0.3, axis='y')

        # Add legend only to first subplot
        if i == 0:
            ax.legend(loc='upper left', bbox_to_anchor=(0, -0.25), ncol=3, frameon=True, fontsize=11)

    fig.tight_layout()
    out = output_dir / "task_success_rates.png"
    fig.savefig(out, dpi=300, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print(f"Saved: {out}")


def plot_duration_distributions(df: pd.DataFrame, duration_stats: dict, output_dir: Path):
    """Box plots showing distribution of actual durations per task with confidence intervals.

    Args:
        df: DataFrame with task completion data
        duration_stats: Pre-computed duration statistics including CIs
        output_dir: Directory where to save the plot
    """
    if df.empty:
        return

    duration_df = df.dropna(subset=['actual_duration_minutes']).copy()
    if duration_df.empty:
        return

    task_label_map = _task_key_to_label_map(df)

    user_types = sorted(duration_df['user_type'].unique().tolist())
    n_user_types = len(user_types)

    # Define colors for user types (consistent with SUS)
    user_type_colors = {
        'end_user': 'lightblue',
        'technician': 'lightcoral'
    }

    # Create figure with vertical layout (one row per user type)
    # Each row has: plot (left) + statistics (right)
    fig = plt.figure(figsize=(10, 5 * n_user_types))
    gs = fig.add_gridspec(n_user_types, 2, width_ratios=[1.5, 1], wspace=0.3,
                         hspace=0.3, top=0.95, bottom=0.05)

    for i, user_type in enumerate(user_types):
        ax_plot = fig.add_subplot(gs[i, 0])
        ax_stats = fig.add_subplot(gs[i, 1])

        ut_df = duration_df[duration_df['user_type'] == user_type].copy()

        # Order tasks by execution order if available
        if "__task_order_idx" in ut_df.columns:
            order_df = ut_df.dropna(subset=['task_key']).groupby('task_key')['__task_order_idx'].min().reset_index()
            order_df.sort_values(['__task_order_idx', 'task_key'], inplace=True)
            task_keys = order_df['task_key'].tolist()
        else:
            task_keys = sorted(ut_df['task_key'].unique().tolist())

        # Prepare data for box plot
        box_data = []
        labels = []
        means = []
        ci_lowers = []
        ci_uppers = []
        stats_lines = ["Duration statistics", ""]

        for task_key in task_keys:
            task_durations = ut_df[ut_df['task_key'] == task_key]['actual_duration_minutes'].values
            if len(task_durations) > 0:
                box_data.append(task_durations)
                task_label = task_label_map[task_key]
                labels.append(task_label)

                # Use pre-computed mean and CI from duration statistics
                task_stats = duration_stats[task_key]
                ut_stats = task_stats['by_user_type'][user_type]
                mean_val = ut_stats['mean']
                ci_lower = ut_stats['ci_95_lower']
                ci_upper = ut_stats['ci_95_upper']
                means.append(mean_val)
                ci_lowers.append(ci_lower)
                ci_uppers.append(ci_upper)

                # Add statistics for this task
                median_val = np.median(task_durations)
                q1 = np.percentile(task_durations, 25)
                q3 = np.percentile(task_durations, 75)
                stats_lines.append(f"{task_label}:")
                stats_lines.append(f"  Count: {len(task_durations)}")
                stats_lines.append(f"  Mean: {np.mean(task_durations):.1f} min")
                stats_lines.append(f"  Median: {median_val:.1f} min")
                stats_lines.append(f"  Q1: {q1:.1f} min")
                stats_lines.append(f"  Q3: {q3:.1f} min")
                stats_lines.append("")

        if not box_data:
            continue

        # Create box plot with blue median line
        bp = ax_plot.boxplot(box_data, tick_labels=labels, patch_artist=True,
                            showmeans=True, meanline=False,
                            medianprops=dict(color='darkblue', linewidth=2.5),
                            meanprops=dict(marker='D', markerfacecolor='red',
                                         markeredgecolor='black', markersize=6))

        # Color boxes based on user type (consistent with SUS)
        box_color = user_type_colors[user_type]
        for patch in bp['boxes']:
            patch.set_facecolor(box_color)
            patch.set_alpha(0.7)

        # Add confidence interval error bars
        x_positions = np.arange(1, len(means) + 1)
        ci_errors = [np.array(means) - np.array(ci_lowers),
                     np.array(ci_uppers) - np.array(means)]

        ax_plot.errorbar(x_positions, means, yerr=ci_errors,
                        fmt='none', ecolor='darkgreen', capsize=5, capthick=2,
                        linewidth=2, alpha=0.8, label='95% CI')

        ax_plot.plot([], [], color='darkblue', linewidth=2.5, label='Median')
        ax_plot.plot([], [], marker='D', color='red', linestyle='None',
                    markeredgecolor='black', markersize=6, label='Mean')
        ax_plot.plot([], [], marker='o', markerfacecolor='none', markeredgecolor='black',
                    linestyle='None', markersize=5, label='Outliers')
        # Position legend based on user type to avoid outlier overlap
        if 'end' in user_type.lower():
            # End user: above plot with more padding from top edge
            ax_plot.legend(loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=2,
                          frameon=True, fontsize=9)
        else:
            # Technician: upper left with padding from edges
            ax_plot.legend(loc='upper left', bbox_to_anchor=(0.02, 0.98), ncol=2,
                          frameon=True, fontsize=9)

        ax_plot.set_ylabel('Duration (min)', fontsize=11)
        ax_plot.set_title(f'Task duration distribution — {_humanize_user_type(user_type)}',
                         fontsize=12)
        ax_plot.set_xticklabels(labels, rotation=30, ha='right')
        ax_plot.grid(True, alpha=0.3, axis='y')

        # Add box plot legend only in the last panel
        if i == n_user_types - 1:
            stats_lines.append("")
            legend_text = get_boxplot_legend_text()
            stats_lines.extend(legend_text.split("\n"))

        # Add statistics panel with box plot legend
        ax_stats.axis('off')
        stats_text = "\n".join(stats_lines)
        ax_stats.text(0.05, 0.95, stats_text, transform=ax_stats.transAxes,
                     fontsize=10, verticalalignment='top', fontfamily='monospace')

    out = output_dir / "task_duration_distributions.png"
    fig.savefig(out, dpi=300, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print(f"Saved: {out}")

def _draw_heatmap(ax: plt.Axes, matrix: np.ndarray, row_labels: List[str], col_labels: List[str], title: str, cmap: str, vmin: float = None, vmax: float = None):
    im = ax.imshow(matrix, aspect='auto', cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=30, ha='right')
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_yticklabels(row_labels)
    ax.set_title(title)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = matrix[i, j]
            if np.isnan(val):
                continue
            ax.text(j, i, f"{val:.0f}", ha='center', va='center', color='black', fontsize=8)
    return im


def plot_error_heatmaps(df: pd.DataFrame, output_dir: Path):
    if df.empty:
        return
    
    # Get task order from metadata
    user_types = sorted(df['user_type'].dropna().unique().tolist())
    if not user_types:
        return
    
    task_label_map = _task_key_to_label_map(df)
    
    # Create separate heatmaps for each user type
    n_user_types = len(user_types)
    fig, axs = plt.subplots(n_user_types, 2, figsize=(14, 5 * n_user_types))
    
    # Ensure axs is always 2D
    if n_user_types == 1:
        axs = axs.reshape(1, -1)

    # Pre-calculate global max values for unified color scales
    global_max_count = 0.0
    global_max_weight = 0.0

    for user_type in user_types:
        ut_df = df[df['user_type'] == user_type].copy()
        if ut_df.empty:
            continue

        participants_raw = sorted(ut_df['participant_id'].dropna().unique().tolist())

        if "__task_order_idx" in ut_df.columns:
            order_df = ut_df.dropna(subset=['task_key']).groupby('task_key')['__task_order_idx'].min().reset_index()
            order_df.sort_values(['__task_order_idx', 'task_key'], inplace=True)
            tasks_keys = order_df['task_key'].tolist()
        else:
            tasks_keys = sorted(ut_df['task_key'].dropna().unique().tolist())

        if not participants_raw or not tasks_keys:
            continue

        pivot_count = ut_df.pivot_table(index='participant_id', columns='task_key', values='errors_encountered', aggfunc='first').reindex(index=participants_raw, columns=tasks_keys)
        pivot_weight = ut_df.pivot_table(index='participant_id', columns='task_key', values='severity_weighted_score', aggfunc='first').reindex(index=participants_raw, columns=tasks_keys)

        max_count = np.nanmax(pivot_count.to_numpy(dtype=float))
        max_weight = np.nanmax(pivot_weight.to_numpy(dtype=float))

        if not np.isnan(max_count):
            global_max_count = max(global_max_count, max_count)
        if not np.isnan(max_weight):
            global_max_weight = max(global_max_weight, max_weight)

    for ut_idx, user_type in enumerate(user_types):
        # Filter data for this user type
        ut_df = df[df['user_type'] == user_type].copy()
        
        if ut_df.empty:
            continue
            
        participants_raw = sorted(ut_df['participant_id'].dropna().unique().tolist())
        participants = [str(p) for p in participants_raw]
        
        # Order tasks by desired execution order for this user type
        if "__task_order_idx" in ut_df.columns:
            order_df = ut_df.dropna(subset=['task_key']).groupby('task_key')['__task_order_idx'].min().reset_index()
            order_df.sort_values(['__task_order_idx', 'task_key'], inplace=True)
            tasks_keys = order_df['task_key'].tolist()
        else:
            tasks_keys = sorted(ut_df['task_key'].dropna().unique().tolist())
        
        tasks = [task_label_map[k] for k in tasks_keys]
        
        if not participants or not tasks:
            continue
        
        # Create pivot tables for this user type
        pivot_count = ut_df.pivot_table(index='participant_id', columns='task_key', values='errors_encountered', aggfunc='first').reindex(index=participants_raw, columns=tasks_keys)
        pivot_weight = ut_df.pivot_table(index='participant_id', columns='task_key', values='severity_weighted_score', aggfunc='first').reindex(index=participants_raw, columns=tasks_keys)
        m_count = pivot_count.to_numpy(dtype=float)
        m_weight = pivot_weight.to_numpy(dtype=float)
        
        # Draw heatmaps for this user type with unified color scales
        im1 = _draw_heatmap(axs[ut_idx, 0], m_count, participants, tasks, f'Errors per Task — {_humanize_user_type(user_type)}', 'Reds', vmin=0, vmax=global_max_count)
        im2 = _draw_heatmap(axs[ut_idx, 1], m_weight, participants, tasks, f'Severity-weighted Score per Task — {_humanize_user_type(user_type)}', 'Oranges', vmin=0, vmax=global_max_weight)
        
        # Add colorbars
        fig.colorbar(im1, ax=axs[ut_idx, 0], fraction=0.046, pad=0.04)
        fig.colorbar(im2, ax=axs[ut_idx, 1], fraction=0.046, pad=0.04)
    
    fig.tight_layout()
    out = output_dir / "task_error_heatmaps.png"
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    output_dir = repo_root / "results" / "aggregated_analysis" / "tasks"
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_rows(repo_root)
    duration_stats = load_duration_statistics(repo_root)

    # Task completion analysis
    plot_success_rates(df, output_dir)
    plot_error_heatmaps(df, output_dir)

    # Duration analysis (essential plots only)
    plot_duration_distributions(df, duration_stats, output_dir)


if __name__ == "__main__":
    main()
