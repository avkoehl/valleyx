import os

from affine import Affine
import numpy as np
import geopandas as gpd
import rioxarray as rxr
import xarray as xr
from shapely.geometry import Point

def pixel_to_point(raster: xr.DataArray, row: int, col: int) -> Point:
    """
    Converts the row and column of a raster array to a geographic Point.

    Parameters
    ----------
    raster : xr.DataArray
        The rioxarray raster from which the coordinate is derived.
    row : int
        The row index (y-coordinate) in the raster array.
    col : int
        The column index (x-coordinate) in the raster array.

    Returns
    -------
    Point
        A Shapely Point representing the geographic coordinates (longitude, latitude).
    """
    transform: Affine = raster.rio.transform()
    lon, lat = transform * (col, row)  # (x, y) corresponds to (col, row)
    return Point(lon, lat)

def translate_to_wbt(pour_points: gpd.GeoSeries, offset: tuple) -> gpd.GeoSeries:
    """
    Translates a points coordinates from the top left of a cell to the center
    of a cell. 
    """
    return pour_points.translate(xoff=offset[0]/2, yoff=offset[1]/2)

def finite_unique(raster: xr.DataArray) -> np.ndarray:
    """
    Returns all unique non-NaN and non-infinite values from a raster array.

    Parameters
    ----------
    raster : xr.DataArray
        The input raster array.

    Returns
    -------
    np.ndarray
        A NumPy array of unique valid values (non-NaN, non-infinite).
    """
    data = raster.values
    uniques = np.unique(data)
    valid_uniques = uniques[np.isfinite(uniques)]
    return valid_uniques
