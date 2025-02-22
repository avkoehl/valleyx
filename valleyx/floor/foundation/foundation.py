"""
Finds all the low slope areas connected to the flowpath network

- smooth
- segment into super pixels
- threshold super pixel regions by slope
- run connectivity algorithm
"""

import numpy as np
from scipy.ndimage import binary_closing
from skimage.segmentation import felzenszwalb
from skimage.morphology import isotropic_dilation

from valleyx.floor.foundation.connect import connected
from valleyx.floor.smooth import filter_nan_gaussian_conserving


def foundation(slope, flowpaths, apst):
    smoothed = filter_nan_gaussian_conserving(slope.data, sigma=3)
    regions = _felzenszwalb_regions(smoothed)
    thresholded, _ = _threshold_region_slope_medians(regions, smoothed, apst)
    base = _connectivity(thresholded, flowpaths, smoothed, apst)
    structure = np.ones((5, 5))
    base.data = binary_closing(base.data, structure=structure, iterations=3)
    return base


def _felzenszwalb_regions(image, scale=100, sigma=0.5, min_size=100):
    regions = felzenszwalb(image, scale=scale, sigma=sigma, min_size=min_size)
    regions = regions.astype(np.float64)
    regions[~np.isfinite(image)] = np.nan
    return regions


def _threshold_region_slope_medians(regions, slope, threshold):
    unique = np.unique(regions)
    unique = unique[np.isfinite(unique)]

    thresholded = np.zeros_like(slope)
    medians = np.zeros_like(slope)

    for region in unique:
        condition = regions == region
        slope_values = slope[condition]
        median_slope = np.median(slope_values)
        medians[condition] = median_slope

        if median_slope <= threshold:
            thresholded[condition] = 1

    return thresholded, medians


def _connectivity(thresholded, flowpaths, slope, apst):
    # try buffering flowpaths (to break entrenchment)
    fp = flowpaths > 0
    dilated = isotropic_dilation(fp, radius=5)
    fp.data = dilated

    result = connected(thresholded, fp)

    result.data[dilated & (slope > apst)] = False
    result.data[flowpaths > 0] = True

    return result
