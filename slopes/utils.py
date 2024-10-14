import os

from pysheds.grid import Grid
from pysheds.view import Raster
from pysheds.view import ViewFinder
from affine import Affine
import numpy as np
import geopandas as gpd
import rioxarray as rxr
import xarray as xr
from shapely.geometry import Point

def rioxarray_to_pysheds(raster: xr.DataArray) -> tuple[Grid, Raster]:

    view = ViewFinder(affine=raster.rio.transform(), 
                      shape = raster.shape,
                      nodata = raster.rio.nodata,
                      crs = raster.rio.crs)
    pysheds_raster = Raster(raster.data, viewfinder=view)

    grid = Grid.from_raster(pysheds_raster)
    return (grid, pysheds_raster)

def pysheds_to_rioxarray(raster: Raster, grid: Grid) -> xr.DataArray:
    da = xr.DataArray(
            data = raster,
            dims = ['y','x'],
            coords = {
                "y": np.linspace(
                    grid.bbox[3], grid.bbox[1], raster.shape[0]),
                "x": np.linspace(
                    grid.bbox[0], grid.bbox[2], raster.shape[1])
                }
            )
    da.rio.write_transform(grid.affine, inplace=True)
    da.rio.write_crs(grid.crs.to_string(), inplace=True)
    da.rio.write_nodata(grid.nodata, inplace=True)
    return da



def wbt_slope():
    """
    wrapper around WBT slope method
    """

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

def observe_values(points: gpd.GeoDataFrame, grid: xr.DataArray | xr.Dataset):
    """
    Add raster values to a GeoDataFrame containing point geometries.

    Parameters
    ----------
    points: gpd.GeoDataFrame
        A GeoDataFrame with point geometries
    grid: xr.DataArray or xr.Dataset
        Either a single raster or a raster stack (Dataset)

    Returns
    -------
        The input GeoDataFrame with additional columns:
        - If a single raster is provided, a new column 'value' is added
          containing the raster value at each point.
        - If a stack of rasters is provided, a new columns is added for each
          layer, named according to the 'datavar' attribute of the layer.
    
    """
    xs = xr.DataArray(points.geometry.x.values, dims='z')
    ys = xr.DataArray(points.geometry.y.values, dims='z')
    values = grid.sel(x=xs, y=ys, method='nearest')

    if isinstance(values, xr.Dataset):
        for key in values:
            points[key] = values[key].values
    else:
        points['value'] = values.values
    return points
