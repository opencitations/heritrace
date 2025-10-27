"""
Common plotting utilities for consistent visualization across analysis modules.

This module provides color schemes, hatch patterns, and helper functions to ensure
that plots are readable both in color and when printed in black and white.
"""

STATUS_COLORS = {
    'complete': '#1b7837',
    'partial': '#fdae61',
    'success_timeout': '#4575b4',
    'failed_misunderstanding': '#d73027',
    'failed_bug': '#7b3294'
}

STATUS_HATCHES = {
    'complete': '',
    'partial': '///',
    'success_timeout': '|||',
    'failed_misunderstanding': 'xxx',
    'failed_bug': '\\\\\\'
}

STATUS_LABELS = {
    'complete': 'Complete',
    'partial': 'Partial',
    'success_timeout': 'Success: Timeout',
    'failed_misunderstanding': 'Failed: Misunderstanding',
    'failed_bug': 'Failed: Bug'
}

SENTIMENT_COLORS = {
    'positive': '#1b7837',  # Green
    'negative': '#d73027'   # Red
}

SENTIMENT_HATCHES = {
    'positive': '',      # No hatch for positive (solid fill)
    'negative': '///'    # Diagonal lines for negative
}

USER_TYPE_COLORS = {
    'end_user': 'lightblue',
    'technician': 'lightcoral'
}
