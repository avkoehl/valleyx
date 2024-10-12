"""
Methods to segment a cross section profile into regions by finding breakpoints

These regions may be:
    - mean shift change point detection on slope using PELT
    - peaks of profile curvature
    - simplification of the elevation profile using Ramer-Douglas-Peucker algorithm

Then we apply a heuristic to classify these regions (find the breakpoint that is most likely valley wall)
in this step we may want to do some preprocessing, e.g. if elevation decreases stop the series

"""
import numpy as np
import ruptures as rpt
from scipy import signal
from rdp import rdp

import matplotlib.pyplot as plt

def mean_shift(series, model='l2', pen=5):
    method = rpt.Pelt(model=model).fit(series)
    result = method.predict(pen=pen)
    labels, bps = label_segments(series, result[:-1])
    return labels, bps

def label_segments(series, bps):
    # confirm that 0 and len(series) are in the breakpoints
    bps = list(bps)
    bps.append(0)
    bps.append(len(series) -1)
    bps = list(set(bps))
    bps.sort()
    labels = np.zeros(len(series), dtype=int)
    for i in range(len(bps) -1):
        start = bps[i]
        end = bps[i+1]
        labels[start:(end+1)] = i
    return labels, bps

def profile_curvature_peaks(curvature_series, find_peaks_params=None):
    if find_peaks_params is not None:
        peak_positions = signal.find_peaks(curvature_series, **find_peaks_params)[0]
    else:
        peak_positions = signal.find_peaks(curvature_series, height=0)[0]
    labels, bps = label_segments(curvature_series, peak_positions)
    return labels, bps

def elevation_simplification(elevation_series, distances_series, epsilon):
    data = np.array(list(zip(distances_series, elevation_series)))
    mask = rdp(data, return_mask=True, algo='iter', epsilon=epsilon)

    # mask to bps
    bps = []
    has_start = False
    for i,element in enumerate(mask):
        if element and not has_start:
            start = i
            has_start = True
        elif element and has_start:
            has_start = False
            bps.append(i)

    labels, bps = label_segments(elevation_series, bps)
    return labels, bps

def plot_segments(alpha_series, value_series, labels, bps):
    fig, ax = plt.subplots()

    ax.scatter(alpha_series, value_series, marker='o')

    colors = ['white', 'lightblue']
    for i in range(len(bps) - 1):
            plt.axvspan(alpha_series.iloc[bps[i]], alpha_series.iloc[bps[i+1]], facecolor=colors[i % 2], alpha=0.5)

    for bp in bps[1:-1]:
        plt.axvline(x=alpha_series.iloc[bp], linestyle='--', color='red', linewidth=1)

    return fig, ax
    
