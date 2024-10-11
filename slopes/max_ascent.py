"""
    TODO: 
       consider improvements to sampling:
          - sample at set distances down the flowpath (convert to linestring)
          - sample a point on either side of the flowpath at the set point so not biasing steeper hillslope

"""
import random

import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from whitebox import WhiteboxTools

from slopes.flow_dir import flowdir_wbt
from slopes.flow_dir import trace_flowpath
from slopes.flow_dir import DIRMAPS
from slopes.utils import finite_unique

def max_ascent_paths(flow_paths: xr.DataArray, dem: xr.DataArray, num_points: int, wbt: WhiteboxTools):
    """
    Trace paths following the maximum local gradient from the streams.

    Parameters
    ----------
    flow_paths: xr.DataArray
        A raster representing the stream_network, each stream cell is labeled
        by stream_id, non stream cells are 0 or NoData
    dem: xr.DataArray
        A raster representing the elevations 
    num_points: int
        The number of points to sample from each stream in the flowpaths raster
    wbt: WhiteboxTools
        An instance of the WhiteboxTools class

    Returns
    -------
    gpd.GeoDataFrame:
        Points representing the paths with the following columns:
            - "geometry": Point
            - "streamID": streamID path starts on
            - "pathID": streamID path starts on
            - "pointID": streamID path starts on
    """

    # invert DEM and then compute flowdirection raster
    # trace paths along that flowdirection raster for each stream
    dem = invert_dem(dem)
    fdir = flowdir_wbt(dem, wbt)
    stream_points = sample_points_on_flowpaths(flow_paths, num_points)

    results = [] 
    for row in stream_points.itertuples(index=False):
        path = trace_flowpath(row.row, row.col, fdir, dirmap=DIRMAPS['wbt'])
        for i,point in enumerate(path):
            result = {'geometry': point,
                      'streamID': row.streamID,
                      'pathID': i}
            results.append(result)
    results = gpd.GeoDataFrame.from_records(results)
    results = results.set_geometry('geometry')
    results.crs = dem.rio.crs
    results['pointID'] = np.arange(len(results))
    return results

def sample_points_on_flowpaths(flow_paths: xr.DataArray, num_points: int) -> list[tuple]:
    """
    Parameters
    ----------
    flow_paths: xr.DataArray
        A raster representing the flow paths
    num_points: 
        Number of points to samplef rom each flow path
    Returns
    -------
    pd.DataFrame:
        A dataframe with the following columns:
        - "streamID" numeric, flowpath ID
        - "row" numeric, row index of point 
        - "col" numeric, col index of point
    """
    points = pd.DataFrame()
    for streamID in finite_unique(flow_paths):
        cells = np.argwhere(flow_paths.data == streamID)
        sample_size = min(len(cells), num_points)
        sampled = random.sample(cells.tolist(), sample_size)
        rows, cols = zip(*sampled)
        stream_df = pd.DataFrame({'streamID': streamID, 'row': rows, 'col': cols})
        points = pd.concat([points, stream_df])

    return points 

def invert_dem(dem: xr.DataArray) -> xr.DataArray:
    """
    Inverts dem so that high points become low points and low points are the
    high points. Maintains the range of values and the minimum elevation.

    Parameters
    ---------
    dem: xr.DataArray
        A raster representing elevations
    Returns
    -------
    xr.DataArray
        A raster representing inverted elevations
    """
    inverted_dem = -1 *  (dem - dem.max().item()) + dem.min().item()
    return inverted_dem
