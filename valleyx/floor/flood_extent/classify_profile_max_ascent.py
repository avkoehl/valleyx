import pandas as pd
import geopandas as gpd
import numpy as np
from loguru import logger
import xarray as xr

from valleyx.floor.flood_extent.path import DIRMAPS, trace_flowpath
from valleyx.floor.flood_extent.split_profile import split_profile
from valleyx.utils.raster import points_to_pixels


def classify_profiles_max_ascent(
    xsections: gpd.GeoDataFrame,
    slope,
    max_ascent_fdir,
    num_cells,
    slope_threshold,
):
    """
    Find the wall points for a stream network's cross sections.
    Using condition on max ascent path of that point

    Parameters
    ----------
    xsections: gpd.GeoDataFrame
        cross sections of the stream network with values for slope, curvature
    slope: xr.DataArray
        slope raster
    num_cells: path length
    slope_threshold: min slope

    Returns
    -------
    gpd.GeoDataFrame
        matches input dataframe with an additional boolean column: 'wallpoint'
    """
    req = ["streamID", "xsID", "alpha", "slope", "curvature"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")

    dirmap = DIRMAPS["wbt"]

    # classify floor points and wall points on each profile
    processed_dfs = []
    grouped = xsections.groupby(["streamID", "xsID"])
    ngroups = len(grouped)

    for i, ((_, _), profile) in enumerate(grouped):
        log_interval = max(1, ngroups // 100)
        if i % log_interval == 0 or i == ngroups:
            percent_complete = (i / ngroups) * 100
            logger.debug(
                f"processing: {i}/{ngroups} ({percent_complete:.2f}% complete)"
            )

        classified = profile.copy()
        classified["bp"] = classified["curvature"] < 0
        rows, cols = points_to_pixels(slope, classified["geom"])
        classified["rows"] = rows
        classified["cols"] = cols

        classified = classify_profile_max_ascent(
            classified, max_ascent_fdir, dirmap, slope, num_cells, slope_threshold
        )
        processed_dfs.append(classified)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df


def classify_profile_max_ascent(
    profile, fdir, dirmap, slope, num_cells, slope_threshold
):
    """for each bp, see if it exceeds num_cells at or above slope_threshold along max ascent path"""

    # split profile
    profile["wallpoint"] = False
    pos, neg = split_profile(profile, duplicate_center=True)

    pos_wall_loc = _find_wall_half_max_ascent(
        pos, fdir, dirmap, slope, num_cells, slope_threshold
    )
    neg_wall_loc = _find_wall_half_max_ascent(
        neg, fdir, dirmap, slope, num_cells, slope_threshold
    )

    if pos_wall_loc is not None:
        # set the next location as wall
        # next_loc = pos.index[pos.index.get_loc(pos_wall_loc) + 1]
        profile.loc[pos_wall_loc, "wallpoint"] = True
    if neg_wall_loc is not None:
        # next_loc = neg.index[neg.index.get_loc(neg_wall_loc) + 1]
        profile.loc[neg_wall_loc, "wallpoint"] = True
    return profile


def _find_wall_half_max_ascent(
    half_profile, fdir, dirmap, slope, num_cells, slope_threshold
):
    half_profile.loc[half_profile.index[0], "bp"] = False  # this is the stream
    half_profile.loc[half_profile.index[0 + 1], "bp"] = (
        True  # this is the cell immediately next to the stream
    )

    bps = half_profile.loc[half_profile["bp"]]

    for ind, bp_row in bps.iterrows():
        row = bp_row["rows"]
        col = bp_row["cols"]
        if is_wall_point(row, col, fdir, dirmap, slope, slope_threshold, num_cells):
            return ind
    return None


def is_wall_point(row, col, fdir, dirmap, slope, slope_threshold, num_cells):
    # get path
    path = trace_flowpath(row, col, fdir, dirmap, num_cells + 1)
    path = path[1:]

    if len(path) < num_cells:
        return False

    slopes = np.zeros(num_cells)
    for i in range(num_cells):
        slopes[i] = slope.data[path[i]].item()

    if np.any(slopes < slope_threshold):
        return False

    return True
