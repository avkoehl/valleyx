"""
Finds all the low slope areas connected to the flowpath network

- smooth
- segment into super pixels
- threshold super pixel regions by slope
- run connectivity algorithm 
"""
import numpy as np
from skimage.morphology import label
from scipy.ndimage import binary_fill_holes
from scipy.ndimage import gaussian_filter
from skimage import filters
from skimage.segmentation import felzenszwalb
from skimage.morphology import label
from skimage.morphology import isotropic_dilation
from skimage.morphology import binary_erosion
from skimage.morphology import binary_dilation

from valleyfloor.floor.connect import connected

def filter_nan_gaussian_conserving(arr, sigma):
    """Apply a gaussian filter to an array with nans.
    https://stackoverflow.com/a/61481246

    Intensity is only shifted between not-nan pixels and is hence conserved.
    The intensity redistribution with respect to each single point
    is done by the weights of available pixels according
    to a gaussian distribution.
    All nans in arr, stay nans in gauss.
    """
    nan_msk = np.isnan(arr)

    loss = np.zeros(arr.shape)
    loss[nan_msk] = 1
    loss = gaussian_filter(
            loss, sigma=sigma, mode='constant', cval=1)

    gauss = arr.copy()
    gauss[nan_msk] = 0
    gauss = gaussian_filter(
            gauss, sigma=sigma, mode='constant', cval=0)
    gauss[nan_msk] = np.nan

    gauss += loss * arr

    return gauss

def foundation(slope, flowpaths, apst):
    smoothed = filter_nan_gaussian_conserving(slope.data, sigma=3)
    regions = _felzenszwalb_regions(smoothed)
    thresholded, _ = _threshold_region_slope_medians(regions, smoothed, apst)
    base = _connectivity(thresholded, flowpaths, smoothed, apst)
    base.data = binary_dilation(base.data)
    base.data = binary_erosion(base.data)
    return base

def _felzenszwalb_regions(image, scale=100, sigma=0.5, min_size=100):
    regions = felzenszwalb(image, scale=scale, sigma=sigma, min_size=min_size)
    regions = regions.astype(np.float64)
    regions[~np.isfinite(image)] = np.nan
    return regions 

def _threshold_region_slope_medians(regions, slope, threshold):
    unique = np.unique(regions)
    unique = unique[np.isfinite(unique)]

    thresholded= np.zeros_like(slope)
    medians= np.zeros_like(slope)

    for region in unique:
        condition = (regions == region)
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
