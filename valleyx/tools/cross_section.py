"""
Code for methods that depend on cross section analysis

1. get points on stream linestring at xs_spacing
2. get points on perpendicular lines to the stream linestring
   at xs_point_spacing up to xs_width on either side of the stream
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from shapely.geometry import LineString, Point, MultiPoint
from shapely.ops import nearest_points

from valleyx.utils.geometry import get_points_on_linestring


def get_cross_section_lines(linestring, xs_spacing, xs_width):
    points = get_points_on_linestring(linestring, xs_spacing)
    width = int(xs_width + 1)
    dfs = []
    for i, point in enumerate(points):
        A, B = _nearest_vertices_on_line(point, linestring)
        xs, ys = _sample_points_on_perpendicular(point, A, B, np.array([-width, width]))
        start = Point(xs[0], ys[0])
        end = Point(xs[1], ys[1])
        xs = LineString([start, end])
        df = pd.DataFrame(
            [{"cross_section_id": i, "center_point": point, "geometry": xs}]
        )
        dfs.append(df)
    df = pd.concat(dfs)
    lines = gpd.GeoDataFrame(df, geometry="geometry")
    return lines


def get_cross_section_points(linestring, xs_spacing, xs_width, xs_point_spacing):
    points = get_points_on_linestring(linestring, xs_spacing)
    alphas = np.arange(-xs_width, xs_width + xs_point_spacing, xs_point_spacing)

    # preallocate arrays:
    total_xs_points = len(points) * len(alphas)
    xsids = np.zeros(total_xs_points, dtype=np.int64)
    all_alphas = np.zeros(total_xs_points, dtype=np.float32)
    xs = np.zeros(total_xs_points, dtype=np.float64)
    ys = np.zeros(total_xs_points, dtype=np.float64)

    # for each point sample points on either side of the linestring
    for i, point in enumerate(points):
        inds = np.arange(i * len(alphas), (i + 1) * len(alphas))
        A, B = _nearest_vertices_on_line(point, linestring)
        pxs, pys = _sample_points_on_perpendicular(point, A, B, alphas)
        xsids[inds] = i
        all_alphas[inds] = alphas
        xs[inds] = pxs
        ys[inds] = pys

    df = pd.DataFrame({"cross_section_id": xsids, "alpha": all_alphas})
    points_df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(xs, ys))
    points_df.rename(columns={"geometry": "point"}, inplace=True)
    return points_df


# --- Internal Functions ----------------------------------------------------- #
def _nearest_vertices_on_line(point, linestring):
    # assumes point is on the linestring
    # so don't need to check against every vertex, just ones that are within a buffer
    linestring = gpd.GeoSeries(linestring).clip(point.buffer(5)).iloc[0]

    if isinstance(linestring, shapely.geometry.multilinestring.MultiLineString):
        ls = gpd.GeoSeries(linestring)
        ls = ls.explode(index_parts=False).reset_index(drop=True)
        closest = ls.loc[ls.distance(point).idxmin()]
        linestring = closest

    mp = MultiPoint(linestring.coords)
    nearest_point = nearest_points(point, mp)[1]
    index = list(linestring.coords).index((nearest_point.x, nearest_point.y))

    if index == 0:
        return [nearest_point, Point(linestring.coords[1])]

    if index == (len(linestring.coords) - 1):
        return [nearest_point, Point(linestring.coords[-2])]

    second_nearest = min(
        Point(linestring.coords[index - 1]),
        Point(linestring.coords[index + 1]),
        key=point.distance,
    )
    return [nearest_point, second_nearest]


def _sample_points_on_perpendicular(point, A, B, alphas):
    length = A.distance(B)
    dx = (A.y - B.y) / length
    dy = (B.x - A.x) / length
    xs = point.x + alphas * dx
    ys = point.y + alphas * dy
    return xs, ys
