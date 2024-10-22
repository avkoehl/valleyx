import pandas as pd
import geopandas as gpd
import numpy as np

from slopes.flow_dir import flowdir_wbt
from slopes.flow_dir import trace_flowpath
from slopes.flow_dir import DIRMAPS

        path = trace_flowpath(row.row, row.col, fdir, dirmap=DIRMAPS['wbt'])

def classify_profiles(xsections: gpd.GeoDataFrame, dem, slope, num_cells, slope_threshold):
    """
    add two columns: wall_point, floor
    """
    req = ["streamID", "xsID", "alpha", "slope", "label", "bp"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")

    dem = invert_dem(dem)
    fdir = flowdir_wbt(dem, wbt)

    # classify floor points and wall points on each profile
    processed_dfs = []
    for (streamID, xsID), profile in xsections.groupby(['streamID', 'xsID']):
        classified = classify_profile_max_ascent(profile, num_cells, slope_threshold, fdir)
        processed_dfs.append(classified)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df

def classify_profile_max_ascent(profile, num_cells, slope_threshold, max_ascent_flowdir, dirmap):
    """ for each bp, see if it exceeds num_cells at or above slope_threshold along max ascent path """

    for bp in profile.loc[profile['bp'], 'geom']:
        print(bp)
        # get row,col in max_ascent_flowdir
        # trace flowpath up to-- num_cells
        # if less than num_cells, continue
        # if np.any(path['slope'] < slope_threshold) continue
    pass

# construct flowdir max ascent version
