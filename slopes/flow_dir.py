import os

import geopandas as gpd
import rioxarray as rxr
from shapely.geometry import Point
from whitebox import WhiteboxTools
import xarray as xr

from slopes.utils import pixel_to_point

DIRMAPS = {
        "esri": {
            32: (-1, -1), # up left
            64: (-1, 0), # up 
            128: (-1, 1), # up right
            16: (0, -1), # left
            0: (0, 0), # stay (terminal cell)
            1: (0, 1), # right
            8: (1, -1), # down left
            4: (1, 0), # down
            2: (1, 1) # down right
            },
        "wbt": {
            64: (-1, -1), # up left
            128: (-1, 0), # up 
            1: (-1, 1), # up right
            32: (0, -1), # left
            0: (0, 0), # stay (terminal cell)
            2: (0, 1), # right
            16: (1, -1), # down left
            8: (1, 0), # down
            4: (1, 1) # down right
            }
        }

def trace_flowpath(row: int, col: int, flow_dir: xr.DataArray, dirmap: dict) -> gpd.GeoSeries
    """
    Traces the flowpath from a given cell.

    Parameters
    ----------
    row: int
        Row index
    col: int
        Column index
    flow_dir: xr.DataArray
        A raster representing the flowdirections
    dirmap: dict
        Direction mappings

    Returns
    -------
    gpd.GeoSeries
        Series of point geometries representing the path
    """
    current_row, current_col = row, col
    nrows, ncols = flow_dir.shape
    path = [(row, col)]

    while True:
        current_direction = flow_dir.data[current_row, current_col]
        if current_direction == 0:
            break

        drow, dcol = dirmap[current_direction]
        next_row = current_row + drow
        next_col = current_col + dcol

        if not (0 <= next_row < nrows and 0 <= next_col < ncols):
            break

        current_row, current_col = next_row, next_col
        path.append((next_row, next_col))

    result = [pixel_to_point(flow_dir, row,col) for row,col in path]
    result = gpd.GeoSeries(result, crs=flow_dir.rio.crs)
    return result

def flowdir_wbt(dem: xr.DataArray, wbt: WhiteboxTools):
    """
    wrapper around whiteboxtools d8 flowdir

    Parameters
    ----------
    dem: xr.DataArray
        A raster representing elevations. For best results ensure it has been
        hydrologically conditioned.
    wbt: Instance of WhiteboxTools

    Returns
    -------
    xr.DataArray
        A raster of flow directions using WhiteBoxTools flow direction mappings
    """
    demfile = os.path.join(wbt.work_dir, 'fdir_dem.tif')
    flowdirfile = os.path.join(wbt.work_dir, 'fdir.tif')

    dem.rio.to_raster(demfile)

    wbt.d8_pointer(
            demfile,
            flowdirfile
            )

    with rxr.open_rasterio(flowdirfile, masked=True) as raster:
        fdir = raster.squeeze().copy()

    return fdir
