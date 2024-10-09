"""
Assumes flowpaths are properly aligned

input:
    flowdir
    flowacc
    flowpaths
output:
    subbasins
"""
import os
import shutil

import geopandas as gpd
import numpy as np
import rioxarray as rxr
from whitebox import WhiteboxTools
from valleyfloor.utils import make_dir
import xarray as xr

from utils import pixel_to_point, translate_to_wbt, finite_unique

def label_subbasins(flow_dir: xr.DataArray, flow_acc: xr.DataArray, flow_paths:
              xr.DataArray, wbt: WhiteboxTools) -> xr.DataArray:
    """
    Labels subbasins for a given flow_path raster

    Parameters
    ----------
    flow_dir: xr.DataArray
        A raster representing the flow direction in whitebox pointer format
    flow_acc: xr.DataArray
        A raster representing the flow accumulation for each cell
    flow_paths: xr.DataArray
        A raster representing the stream_network, each stream cell is labeled
        by stream_id, non stream cells are 0 or NoData
    wbt: WhiteBoxTools
        An instance of the WhiteboxTools class

    Returns
    -------
    subbasins: xr.DataArray
        A raster with each subbasin labeled according to which segment in the
        stream network that cell flows into. Labels follow the labels used 
        by 'flow_paths' input
    """
    pour_points = _pour_points_from_flowpaths(flow_paths, flow_acc)

    work_dir = wbt.work_dir
    temp_dir = os.path.join(work_dir, 'subbasin_temp')
    make_dir(temp_dir)
    files = {
            'temp_flowdir': os.path.join(temp_dir, 'temp_flowdir.tif'),
            'temp_pour_points': os.path.join(temp_dir, 'temp_pour_points.shp'),
            'subbasins': os.path.join(work_dir, 'subbasins.tif')}
    flow_dir.rio.to_raster(files['temp_flowdir'])
    pour_points.to_file(files['temp_pour_points'])

    wbt.watershed(
            files['temp_flowdir'],
            files['temp_pour_points'],
            files['subbasins'])

    with rxr.open_rasterio(files['subbasins'], masked=True) as raster:
        subbasins = raster.squeeze().copy()

    shutil.rmtree(temp_dir)
    return subbasins


def _pour_points_from_flowpaths(flow_paths: xr.DataArray, flow_acc:
                                xr.DataArray) -> gpd.GeoSeries: 
    """
    Returns outlet cell for each stream 
    where the outlet cell is the cell with the maximum flow accumulation value

    Parameters
    ----------
    flow_paths: xr.DataArray
        A raster representing the stream_network, each stream cell is labeled
        by stream_id, non stream cells are 0 or NoData
    flow_acc: xr.DataArray
        A raster representing flow accumulation for each cell

    Returns
    -------
    pour_points: gpd.GeoDataFrame
    """
    pour_points_list = []
    
    for streamID in finite_unique(flow_paths):
        stream_mask = (flow_paths == streamID)
        fa_values = np.where(stream_mask, flow_acc.values, np.nan)
        max_idx = np.unravel_index(np.nanargmax(fa_values), fa_values.shape)
        row, col = max_idx
        pour_point = pixel_to_point(flow_paths, row, col)
        pour_points_list.append(pour_point)

    pour_points = gpd.GeoSeries(pour_points_list, crs=flow_paths.rio.crs)
    pour_points = translate_to_wbt(pour_points, flow_paths.rio.resolution())
    return pour_points
