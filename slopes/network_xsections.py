"""
Create cross section profiles for given raster(s) and flowlines

inputs:
    flowlines
    grid
    [subbasins]
    line_spacing
    line_width
    point_spacing

outputs:
    lines
    points
"""
from typing import Optional
from typing import Union

import numpy as np
import xarray as xr
import pandas as pd
import geopandas as gpd

from valleyfloor.raster.vectorize import single_polygon_from_binary_raster
from valleyfloor.geometry.utils import get_length_and_width

from valleyfloor.geometry.cross_section import get_points_on_linestring
from valleyfloor.geometry.cross_section import get_cross_section_points_from_points
from valleyfloor.geometry.utils import get_length_and_width
from shapely.geometry import LineString
from shapelysmooth import chaikin_smooth
from shapelysmooth import taubin_smooth

def network_xsections(flowlines: gpd.GeoDataFrame, grid:
                      Union[xr.Dataset, xr.DataArray], line_spacing: int,
                      line_width: int, point_spacing: int, subbasins:
                      Optional[xr.DataArray] = None) -> gpd.GeoDataFrame:
    """
    Create cross section profiles for a stream network and a given raster or stack of rasters.

    Parameters
    ----------
    flowlines: gpd.GeoSeries[LineString]
        A series of flowline geometries
    grid: xr.Dataset | xr.DataArray
        A raster or stack of rasters to select values from for the cross section profiles
    line_spacing: int
        The distance between cross sections
    line_width: int
        The length of each cross section
    point_spacing: int
        The distance between points to observe along each cross section line
    subbasins: Optional[xr.DataArray], optional
        An optional subbasin raster, if provided, this will make it so that the
        cross section widths are clipped to the subbasin dimensions for the
        subbasin that matches with each flowline.

    Returns
    -------
    xsections: gpd.GeoDataFrame
    """
    xsections = gpd.GeoDataFrame()

    for streamID in flowlines['Stream_ID']:
        flowline = flowlines.loc[flowlines['Stream_ID'] == streamID, 'geometry'].iloc[0]

        if subbasins is not None:
            poly = single_polygon_from_binary_raster(subbasins == streamID)
            width = int(max(get_length_and_width(poly)) + 1)
            xspoints = flowline_xsections(flowline, line_spacing, width, point_spacing)
            xspoints = xspoints.clip(poly)
        else:
            xspoints = flowline_xsections(flowline, line_spacing, line_width, point_spacing)

        xspoints['streamID'] = streamID
        xsections = pd.concat([xsections, xspoints], ignore_index=True)
            
    xsections = observe_values(xsections, grid)
    return xsections

def flowline_xsections(flowline: LineString, line_spacing: int, line_width:
                       int, point_spacing: int) -> gpd.GeoDataFrame:
    """
    Create cross section profiles for a single flowline. 

    Parameters
    ---------
    flowline: LineString
        A single flowline
    line_spacing: int
        distance between cross sections
    line_width: int
        length of the cross section
    point_spacing: int
        distance between points to observe along each cross section line

    Returns
    -------
    xspoints: gpd.GeoDataFrame
    """
    flowline = flowline.simplify(20)
    flowline = chaikin_smooth(taubin_smooth(flowline))

    points = get_points_on_linestring(flowline, line_spacing) 
    xspoints = get_cross_section_points_from_points(flowline, points,
                                                   line_width, point_spacing)
    return xspoints

def observe_values(points: gpd.GeoDataFrame, grid: xr.DataArray | xr.Dataset):
    """
    Get the values at a set of input points. Works on a single raster or a raster stack (xr.Dataset).
    Will create a new column for each raster in the stack.

    Parameters
    ----------
    points: gpd.GeoDataFrame
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
