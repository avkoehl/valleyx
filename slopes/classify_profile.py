import pandas as pd
import geopandas as gpd
import numpy as np

from slopes.preprocess_profile import _split_profile


def classify_profiles(xsections: gpd.GeoDataFrame, slope_threshold=12.5) -> gpd.GeoDataFrame: 
    """
    add two columns: wall_point, floor
    """
    req = ["streamID", "xsID", "alpha", "slope", "bp"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")

    # classify floor points and wall points on each profile
    processed_dfs = []
    for (streamID, xsID), profile in xsections.groupby(['streamID', 'xsID']):
        classified = classify_profile_slope_threshold(profile, slope_threshold)
        processed_dfs.append(classified)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df

def classify_profile_slope_threshold(profile, slope_threshold):
    profile['wallpoint'] = False

    pos, neg = _split_profile(profile, duplicate_center=True)
    pos_wall_loc = _find_wall_half(pos, slope_threshold)
    neg_wall_loc = _find_wall_half(neg, slope_threshold)

    if pos_wall_loc is not None:
        profile.loc[pos_wall_loc, "wallpoint"] = True
    if neg_wall_loc is not None:
        profile.loc[neg_wall_loc, "wallpoint"] = True
    return profile

def _find_wall_half(half_profile, slope_threshold):
    """
    returns wall point loc if any
    """
    # add first and last point as bps
    half_profile.loc[half_profile.index[0], 'bp'] = True # this is the stream
    half_profile.loc[half_profile.index[-1], 'bp'] = True

    positional_indices = np.where(half_profile['bp'])[0]

    for i,position in enumerate(positional_indices):
        if i == (len(positional_indices) - 1): # final index
            break
        
        next_pos = positional_indices[i+1]
        median_slope = half_profile['slope'].iloc[position: next_pos+1].median()

        if median_slope > slope_threshold:
            return half_profile.index[position]
    return None