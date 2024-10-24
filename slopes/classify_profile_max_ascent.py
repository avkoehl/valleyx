import pandas as pd
import geopandas as gpd
import numpy as np

from slopes.flow_dir import flowdir_wbt
from slopes.flow_dir import trace_flowpath
from slopes.flow_dir import DIRMAPS
from slopes.max_ascent import invert_dem
from slopes.preprocess_profile import _split_profile
from slopes.utils import point_to_pixel
from slopes.utils import pixel_to_point

from tqdm import tqdm


def classify_profiles_max_ascent(xsections: gpd.GeoDataFrame, dem, slope, num_cells, slope_threshold, wbt):
    """
    add two columns: wall_point, floor
    """
    req = ["streamID", "xsID", "alpha", "slope", "bp"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")

    inverted_dem = invert_dem(dem)
    fdir = flowdir_wbt(inverted_dem, wbt)
    dirmap = DIRMAPS['wbt']

    # classify floor points and wall points on each profile
    processed_dfs = []
    for (streamID, xsID), profile in tqdm(xsections.groupby(['streamID', 'xsID'])):
        profile['wallpoint'] = False
        classified = classify_profile_max_ascent(profile, fdir, dirmap, slope,
                                                 num_cells, slope_threshold)
        processed_dfs.append(classified)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df

def classify_profile_max_ascent(profile, fdir, dirmap, slope, num_cells, slope_threshold):
    """ for each bp, see if it exceeds num_cells at or above slope_threshold along max ascent path """

    # split profile
    pos, neg = _split_profile(profile, duplicate_center=True)

    pos_wall_loc = _find_wall_half_max_ascent(pos, fdir, dirmap, slope, num_cells, slope_threshold)
    neg_wall_loc = _find_wall_half_max_ascent(neg, fdir, dirmap, slope, num_cells, slope_threshold)

    if pos_wall_loc is not None:
        profile.loc[pos_wall_loc, "wallpoint"] = True
    if neg_wall_loc is not None:
        profile.loc[neg_wall_loc, "wallpoint"] = True
    return profile

def _find_wall_half_max_ascent(half_profile, fdir, dirmap, slope, num_cells, slope_threshold):
    # add first and last point as bp
    half_profile.loc[half_profile.index[0], 'bp'] = True # this is the stream
    half_profile.loc[half_profile.index[-1], 'bp'] = True

    bps = half_profile.loc[half_profile['bp'], 'geom']

    for ind, point in bps.items():
        if is_wall_point(point, fdir, dirmap, slope, slope_threshold, num_cells):
            return ind
    return None

def is_wall_point(point, fdir, dirmap, slope, slope_threshold, num_cells):
    # get path
    row, col = point_to_pixel(fdir, point)
    points, path = trace_flowpath(row, col, fdir, dirmap, num_cells)

    if len(path) < num_cells:
        return False

    slopes = np.zeros(num_cells)
    for i in range(num_cells):
        slopes[i] = slope.data[path[i]].item()

    if np.any(slopes < slope_threshold):
        return False

    return True
