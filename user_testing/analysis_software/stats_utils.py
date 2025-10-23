"""
Common statistical calculations used across different analysis modules
"""

import numpy as np
from scipy import stats
from typing import Tuple


def get_boxplot_legend_text() -> str:
    """Get standardized box plot elements description text.

    Returns:
        Formatted text explaining box plot elements with line wrapping
    """
    return (
        "Box plot elements:\n"
        "• Box edges: 25th (Q1) and 75th (Q3)\n"
        "  percentiles (interquartile range, IQR)\n"
        "• Blue line: Median (50th percentile)\n"
        "• Red diamond: Mean\n"
        "• Green bars: 95% confidence interval\n"
        "  for the mean (t-Student)\n"
        "• Whiskers: Extend to the most extreme\n"
        "  data point within 1.5×IQR from box edges\n"
        "• Circles: Outliers (values beyond\n"
        "  1.5×IQR from box edges)"
    )


def calculate_mean_confidence_interval(data: np.ndarray, confidence: float = 0.95) -> Tuple[float, float, float]:
    """Calculate mean and its confidence interval using t-Student distribution.

    Args:
        data: Array of numeric values
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (mean, ci_lower, ci_upper)
    """
    n = len(data)

    if n == 0:
        return (float('nan'), float('nan'), float('nan'))

    mean_val = float(np.mean(data))

    if n == 1:
        # Single observation: no confidence interval
        return (mean_val, mean_val, mean_val)

    # Calculate 95% CI using t-Student distribution
    ci = stats.t.interval(confidence, n - 1, loc=mean_val, scale=stats.sem(data))
    ci_lower = float(ci[0])
    ci_upper = float(ci[1])

    return (mean_val, ci_lower, ci_upper)
