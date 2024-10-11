"""
Methods to segment a cross section profile into regions by finding breakpoints

These regions may be:
    - mean shift change point detection on slope
    - peaks of profile curvature
    - simplification of the elevation profile using Ramer-Douglas-Peucker algorithm

Then we apply a heuristic to classify these regions (find the breakpoint that is most likely valley wall)
in this step we may want to do some preprocessing, e.g. if elevation decreases stop the series

"""
from sklearn.cluster import MeanShift

def mean_shift(series):
    method = MeanShift()
    method.fit(series.values.reshape(-1,1))
    return method.labels_

def profile_curvature_peaks(series, height):
    peak_positions = signal.find_peaks(series, height)[0]
    pass

def elevation_simplifcation(series):
    # convert series to points (alpha, elevation) to linetring
    #linestring.simpligy
    pass
    
