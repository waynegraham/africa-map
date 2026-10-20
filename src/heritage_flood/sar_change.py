"""Exploratory SAR change calculations; not a flood classifier."""

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def smooth_power(db, *, window=3):
    """Full-neighborhood box mean in linear power; incomplete support stays NaN."""
    values = np.asarray(db, dtype=float)
    if values.ndim < 2 or np.isinf(values).any():
        raise ValueError("Expected spatial dB arrays with finite values or NaN")
    if isinstance(window, bool) or not isinstance(window, int) or window < 1 or window % 2 != 1:
        raise ValueError("Window must be a positive odd integer")
    power = np.power(10.0, values / 10.0)
    padding = [(0, 0)] * (values.ndim - 2) + [(window // 2, window // 2)] * 2
    neighborhoods = sliding_window_view(np.pad(power, padding, constant_values=np.nan),
                                        (window, window), axis=(-2, -1))
    return neighborhoods.mean(axis=(-2, -1))


def analyze_sar(pre_db, post_db, *, window=3):
    """Compute post-minus-power-baseline dB changes and a withheld pre-event check.

    Reference-selection spread uses the first two pre-event dates only. With
    three or more dates, the last pre-event date is withheld from that selector
    and compared with the mean of preceding dates. All required dates/bands
    need full spatial support; no missing pixels are filled or treated as dry.
    """
    pre, post = np.asarray(pre_db, dtype=float), np.asarray(post_db, dtype=float)
    if pre.ndim != 4 or post.ndim != 3 or pre.shape[0] < 2 or pre.shape[1] != 2 or pre.shape[1:] != post.shape:
        raise ValueError("Expected pre[date, VV/VH, row, col] and post[VV/VH, row, col]")
    pre_power, post_power = smooth_power(pre, window=window), smooth_power(post, window=window)
    baseline = 10 * np.log10(pre_power.mean(axis=0))
    filtered_post = 10 * np.log10(post_power)
    pre_filtered_db = 10 * np.log10(pre_power)
    spread = np.max(np.abs(pre_filtered_db[1] - pre_filtered_db[0]), axis=0)
    training_baseline = 10 * np.log10(pre_power[:-1].mean(axis=0))
    holdout = pre_filtered_db[-1] - training_baseline
    return {"baseline_db": baseline, "post_db": filtered_post,
            "delta_db": filtered_post - baseline,
            "reference_pair_spread_db": spread, "holdout_delta_db": holdout,
            "post_vs_training_delta_db": filtered_post - training_baseline}
