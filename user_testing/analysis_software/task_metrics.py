#!/usr/bin/env python3
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

SEVERITY_WEIGHTS = {"low": 1, "medium": 2, "high": 4}

DEFAULT_TASK_KEY_ORDER_BY_USER_TYPE: Dict[str, List[str]] = {
    "end_user": [
        "edit_publication",
        "merge_authors",
        "restore_version",
        "create_publication",
    ],
    "technician": [
        "add_shacl_validation",
        "add_display_support",
    ],
}


def parse_duration_to_minutes(value: Any) -> float:
    if value is None:
        return float("nan")
    s = str(value).strip()
    m = re.fullmatch(r"(\d{1,3}):([0-5]\d):([0-5]\d)", s)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2))
        ss = int(m.group(3))
        return hh * 60 + mm + ss / 60.0
    return float("nan")


def load_task_completion_files(base_dir: Path) -> List[Path]:
    paths: List[Path] = []
    for user_dir in ["endusers", "technicians"]:
        tc_dir = base_dir / "results" / user_dir / "task_completion"
        if tc_dir.exists():
            paths.extend(sorted(tc_dir.glob("*_task_completion.json")))
    return paths


def build_task_key_order_by_user_type(df: pd.DataFrame) -> Dict[str, List[str]]:
    if df.empty:
        return {}

    order_by_user_type: Dict[str, List[str]] = {}
    for user_type, group in df.groupby("user_type"):
        # Collect unique task_keys for this user_type preserving first-seen order
        seen: set = set()
        task_keys: List[str] = []
        for task_key in group["task_key"].tolist():
            if task_key not in seen:
                seen.add(task_key)
                task_keys.append(task_key)

        # Apply explicit default order if provided, keeping only present keys,
        # and append any extra keys that are not in the default list.
        default_order = DEFAULT_TASK_KEY_ORDER_BY_USER_TYPE.get(user_type, [])
        if default_order:
            ordered = [k for k in default_order if k in task_keys] + [k for k in task_keys if k not in default_order]
        else:
            ordered = task_keys

        order_by_user_type[user_type] = ordered

    return order_by_user_type


def compute_row_metrics(record: Dict[str, Any], task_key: str, task: Dict[str, Any]) -> Dict[str, Any]:
    participant_id = record.get("participant_id")
    user_type = record.get("user_type")
    expected_minutes = task.get("expected_duration_minutes")
    actual_minutes = parse_duration_to_minutes(task.get("actual_duration_minutes"))
    status = task.get("status")
    errors = task.get("errors", []) or []
    errors_encountered = int(task.get("errors_encountered", len(errors)) or 0)

    severity_weighted_score = 0
    blocked = False
    for e in errors:
        sev = str(e.get("severity", "")).lower()
        severity_weighted_score += SEVERITY_WEIGHTS.get(sev, 0)
        if sev == "high" and str(e.get("outcome", "")).lower() == "blocked":
            blocked = True

    error_rate_per_minute = (errors_encountered / actual_minutes) if actual_minutes and not np.isnan(actual_minutes) and actual_minutes > 0 else float("nan")

    return {
        "participant_id": participant_id,
        "user_type": user_type,
        "task_key": task_key,
        "task_name": task.get("task_name"),
        "expected_duration_minutes": expected_minutes,
        "actual_duration_minutes": actual_minutes,
        "status": status,
        "errors_encountered": errors_encountered,
        "severity_weighted_score": severity_weighted_score,
        "error_rate_per_minute": error_rate_per_minute,
        "blocked": blocked,
    }


def build_success_rates(df: pd.DataFrame, task_key_order_by_user_type: Dict[str, List[str]]) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    if df.empty:
        return results

    for user_type, group in df.groupby("user_type"):
        task_stats: List[Dict[str, Any]] = []
        for task_key, g in group.groupby("task_key"):
            total = len(g)
            complete = int((g["status"].astype(str).str.lower() == "complete").sum())
            partial = int((g["status"].astype(str).str.lower() == "partial").sum())
            failed = int((g["status"].astype(str).str.lower() == "failed").sum())
            weighted_success = (complete + 0.5 * partial)
            success_rate = (weighted_success / total) * 100.0 if total > 0 else float("nan")
            task_stats.append({
                "task_key": task_key,
                "total": total,
                "complete": complete,
                "partial": partial,
                "failed": failed,
                "success_rate": success_rate,
            })
        if not task_stats:
            results[user_type] = []
            continue
        # Order according to execution order when available
        desired_order = task_key_order_by_user_type.get(user_type, [])
        order_index = {k: i for i, k in enumerate(desired_order)}
        results[user_type] = sorted(
            task_stats,
            key=lambda x: (order_index.get(x["task_key"], 10_000), x["task_key"]),
        )
    return results


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    results_root = repo_root / "results"
    output_dir = results_root / "aggregated_analysis" / "tasks"
    output_dir.mkdir(parents=True, exist_ok=True)

    files = load_task_completion_files(repo_root)
    rows: List[Dict[str, Any]] = []

    for path in files:
        try:
            record = json.loads(path.read_text())
        except Exception:
            continue
        tasks = record.get("tasks", {}) or {}
        for task_key, task in tasks.items():
            rows.append(compute_row_metrics(record, task_key, task))

    df = pd.DataFrame(rows)

    task_key_order_by_user_type = build_task_key_order_by_user_type(df)

    success_rates = build_success_rates(df, task_key_order_by_user_type)

    rows_out = json.loads(df.to_json(orient="records")) if not df.empty else []
    metrics = {
        "rows": rows_out,
        "success_rates": success_rates,
        "metadata": {
            "participants": sorted(df["participant_id"].dropna().unique().tolist()) if not df.empty else [],
            "tasks": sorted(df["task_key"].dropna().unique().tolist()) if not df.empty else [],
            "user_types": sorted(df["user_type"].dropna().unique().tolist()) if not df.empty else [],
            # Execution order of tasks by user type (explicit defaults applied)
            "task_order_by_user_type": task_key_order_by_user_type,
        },
    }

    json_path = output_dir / "task_metrics.json"

    with open(json_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved: {json_path}")
    


if __name__ == "__main__":
    main()
