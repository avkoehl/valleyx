"""
slope
curvature
filters (smooth dem, sobel?)
"""
import os

import rioxarray as rxr

from valleyx.floor.foundation import filter_nan_gaussian_conserving

def elev_derivatives(dem, wbt, sigma):
    work_dir = wbt.work_dir
    # gaussian smooth
    smoothed = dem.copy()
	
	# 
    smoothed.data = filter_nan_gaussian_conserving(dem.data, sigma=sigma)

    files = {
             "smoothed_dem": os.path.join(work_dir, "smoothed_dem.tif"),
             "slope": os.path.join(work_dir, "slope.tif"),
             "profile_curvature": os.path.join(work_dir, "profile_curvature.tif")}

    smoothed.rio.to_raster(files['smoothed_dem'])

    slope = wbt.slope(files['smoothed_dem'], files['slope'], units='degrees')
    curvature = wbt.profile_curvature(files['smoothed_dem'], files['profile_curvature'])

    # read in
    slope = rxr.open_rasterio(files['slope'], masked=True).squeeze()
    curvature = rxr.open_rasterio(files['profile_curvature'], masked=True).squeeze()

    return smoothed, slope, curvature
