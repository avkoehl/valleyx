from typing import Optional

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

def network_xsections(flowlines: gpd.GeoSeries, line_spacing: int, line_width:
                      int, point_spacing: int, subbasins:
                      Optional[xr.DataArray] = None) -> gpd.GeoDataFrame:
    """
    Create cross section profiles for a stream network and a given raster or stack of rasters.

    Parameters
    ----------
    flowlines: gpd.GeoSeries[LineString]
        A series of flowline geometries
    line_spacing: int
        The distance between cross sections
    line_width: int
        The length of each cross section
    point_spacing: int
        The distance between points to observe along each cross section line
    subbasins: Optional[xr.DataArray], optional
        An optional subbasin raster, if provided, this will make it so that the
        cross section widths are clipped to the subbasin dimensions for the
        subbasin that matches with each flowline. Values must match the index
        in flowlines series.

    Returns
    -------
    gpd.GeoDataFrame
        A geodataframe with the following columns:
        - "geom": Point, a point along the xsection profile
        - "pointID": numeric,  cross section id specific to the flowline
        - "streamID': numeric, from the index of flowlines
        - "xsID": numeric,  cross section id specific to the flowline
        - "alpha": numeric, represents the distance from the center point of the xsection
    """
    xsections = gpd.GeoDataFrame()

    for streamID, flowline in flowlines.items():
        if subbasins is not None:
            poly = single_polygon_from_binary_raster(subbasins == streamID)
            width = int(max(get_length_and_width(poly)) + 1)
            xspoints = flowline_xsections(flowline, line_spacing, width, point_spacing)
            xspoints = xspoints.clip(poly)
        else:
            xspoints = flowline_xsections(flowline, line_spacing, line_width, point_spacing)

        xspoints['streamID'] = streamID
        xsections = pd.concat([xsections, xspoints], ignore_index=True)
            
    xsections = xsections.sort_values(by=['streamID', 'xsID', 'alpha'])
    xsections['pointID'] = np.arange(len(xsections))

    order = ['geom', 'pointID', 'streamID', 'xsID', 'alpha']
    xsections = xsections[order]
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
    gpd.GeoDataFrame
        A geodataframe with the following columns:
        - "geom": Point, a point along the xsection profile
        - "alpha": numeric, represents the distance from the center point of the xsection
        - "xsID": numeric,  cross section id specific to the flowline
    """
    flowline = flowline.simplify(20)
    flowline = chaikin_smooth(taubin_smooth(flowline))

    points = get_points_on_linestring(flowline, line_spacing) 
    xspoints = get_cross_section_points_from_points(flowline, points,
                                                   line_width, point_spacing)
    xspoints = xspoints.rename(columns={'alpha': 'alpha', 'point': 'geom', 'cross_section_id': 'xsID'})
    xspoints = xspoints[['geom', 'xsID', 'alpha']]
    xspoints = xspoints.set_geometry('geom')
    return xspoints

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
