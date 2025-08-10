#!/usr/bin/env python3
import json
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_rows(repo_root: Path) -> pd.DataFrame:
    json_path = repo_root / "results" / "aggregated_analysis" / "tasks" / "task_metrics.json"
    if not json_path.exists():
        return pd.DataFrame()
    with open(json_path, "r") as f:
        data = json.load(f)
    rows = data.get("rows", [])
    df = pd.DataFrame(rows)
    # Attach desired order per user type if present in metadata
    metadata = data.get("metadata", {})
    order_by_user_type = metadata.get("task_order_by_user_type", {})
    if not df.empty and order_by_user_type:
        def order_index(row):
            desired = order_by_user_type.get(str(row.get('user_type')), [])
            try:
                return desired.index(row.get('task_key'))
            except Exception:
                return 10_000
        df['__task_order_idx'] = df.apply(order_index, axis=1)
    return df


def _humanize_text(value: str) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).replace("_", " ").strip().title()


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
    def _weighted_rate(s: pd.Series) -> float:
        status = s.astype(str).str.lower()
        complete = (status == 'complete').sum()
        partial = (status == 'partial').sum()
        total = len(status)
        return ((complete + 0.5 * partial) / total) * 100.0 if total > 0 else np.nan
    group_cols = ["user_type", "task_key"]
    rates = df.groupby(group_cols)['status'].apply(_weighted_rate).reset_index(name='success_rate')
    # If an order index is available, carry it for sorting within each user_type
    if "__task_order_idx" in df.columns:
        order_idx = df.groupby(group_cols)['__task_order_idx'].min().reset_index(name='order_idx')
        rates = rates.merge(order_idx, on=group_cols, how='left')
    user_types = sorted(rates['user_type'].unique().tolist())
    n = len(user_types)
    fig, axs = plt.subplots(1, n, figsize=(6 * n, 5), squeeze=False)
    for i, ut in enumerate(user_types):
        ax = axs[0, i]
        sub = rates[rates['user_type'] == ut].copy()
        if 'order_idx' in sub.columns:
            sub.sort_values(['order_idx', 'task_key'], inplace=True)
        else:
            sub.sort_values('task_key', inplace=True)
        labels = [task_label_map.get(k, _humanize_text(k)) for k in sub['task_key'].tolist()]
        ax.bar(np.arange(len(sub)), sub['success_rate'].values, color='steelblue', alpha=0.9)
        ax.set_xticks(np.arange(len(sub)))
        ax.set_xticklabels(labels, rotation=30, ha='right')
        ax.set_ylim(0, 100)
        ax.set_ylabel('Success %')
        ax.set_title(f'Task Success Rate — {_humanize_user_type(ut)}')
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = output_dir / "task_success_rates.png"
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


def plot_duration_expected_vs_actual(df: pd.DataFrame, output_dir: Path):
    if df.empty:
        return
    plot_df = df.dropna(subset=['expected_duration_minutes', 'actual_duration_minutes']).copy()
    if plot_df.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 6))
    for ut, sub in plot_df.groupby('user_type'):
        ax.scatter(sub['expected_duration_minutes'], sub['actual_duration_minutes'], label=_humanize_user_type(ut), alpha=0.85)
    lim = max(plot_df['expected_duration_minutes'].max(), plot_df['actual_duration_minutes'].max())
    ax.plot([0, lim], [0, lim], ls='--', c='gray', alpha=0.7)
    ax.set_xlabel('Expected duration (min)')
    ax.set_ylabel('Actual duration (min)')
    ax.set_title('Duration: Expected vs Actual')
    ax.legend()
    ax.grid(True, alpha=0.3)
    out = output_dir / "task_duration_expected_vs_actual.png"
    fig.tight_layout()
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


def _draw_heatmap(ax: plt.Axes, matrix: np.ndarray, row_labels: List[str], col_labels: List[str], title: str, cmap: str):
    im = ax.imshow(matrix, aspect='auto', cmap=cmap)
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
        
        tasks = [task_label_map.get(k, _humanize_text(k)) for k in tasks_keys]
        
        if not participants or not tasks:
            continue
        
        # Create pivot tables for this user type
        pivot_count = ut_df.pivot_table(index='participant_id', columns='task_key', values='errors_encountered', aggfunc='first').reindex(index=participants_raw, columns=tasks_keys)
        pivot_weight = ut_df.pivot_table(index='participant_id', columns='task_key', values='severity_weighted_score', aggfunc='first').reindex(index=participants_raw, columns=tasks_keys)
        m_count = pivot_count.to_numpy(dtype=float)
        m_weight = pivot_weight.to_numpy(dtype=float)
        
        # Draw heatmaps for this user type
        im1 = _draw_heatmap(axs[ut_idx, 0], m_count, participants, tasks, f'Errors per Task — {_humanize_user_type(user_type)}', 'Reds')
        im2 = _draw_heatmap(axs[ut_idx, 1], m_weight, participants, tasks, f'Severity-weighted Score per Task — {_humanize_user_type(user_type)}', 'Oranges')
        
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

    plot_success_rates(df, output_dir)
    plot_duration_expected_vs_actual(df, output_dir)
    plot_error_heatmaps(df, output_dir)


if __name__ == "__main__":
    main()
