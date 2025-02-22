import numpy as np
import xarray as xr
from shapely.geometry import Point


def point_to_pixel(raster: xr.DataArray, point: Point) -> tuple[int, int]:
    """
    Converts shapely point to the row and col index of that point according
    to the affine transformation of the input raster

    Parameters
    ----------
    raster: xr.DataArray
        raster from which we will use the Affine transform
    point: shapely.geometry.Point
        shapely point we want the coordinate for

    Returns
    -------
    tuple:
        (row, col)
    """
    transform = raster.rio.transform()
    inverse = ~transform
    lon = point.x
    lat = point.y
    col, row = inverse * (lon, lat)
    return int(row), int(col)


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
    transform = raster.rio.transform()
    lon, lat = transform * (col, row)  # (x, y) corresponds to (col, row)
    # offset by half a pixel to get the center of the pixel
    lon += transform.a / 2
    lat += transform.e / 2
    return Point(lon, lat)


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
