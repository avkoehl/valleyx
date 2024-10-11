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

def mean_shift(series, model='l2', pen=5):
    method = rpt.Pelt(model=model).fit(series)
    result = method.predict(pen=pen)
    labels = label_segments(series, bps)
    return labels


def label_segments(series, bps):
    labels = np.zeros(len(series), dtype=int)
    for i in range(len(bps) -1):
        start = bps[i]
        end = bps[i+1]
        labels[start:end] = i
    return labels


def profile_curvature_peaks(series, height):
    peak_positions = signal.find_peaks(series, height)[0]
    labels = label_segments(series, peak_positions)
    return labels

def elevation_simplifcation(series):
    # convert series to points (alpha, elevation) to linetring
    #linestring.simplify
    pass

def plot_segments(series, labels):
    pass
    
