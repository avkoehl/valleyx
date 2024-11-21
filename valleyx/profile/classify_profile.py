import pandas as pd
import geopandas as gpd
import numpy as np
from scipy import signal
from loguru import logger

from valleyx.profile.split import split_profile

def classify_profiles(xsections: gpd.GeoDataFrame, slope_threshold: int,
                      distance: int, height: float) -> gpd.GeoDataFrame: 
    """
    Find the wall points for a stream network's cross sections.
    Using a slope threshold

    Parameters
    ----------
    xsections: gpd.GeoDataFrame
        cross sections of the stream network with values for slope, curvature
    slope_threshold: int
        maximum slope of a region in the cross section before it gets
        classified as valley wall
    distance: int
        distance parameter of signal.find_peaks
    height: float
        height parameter of signal.find_peaks


    Returns
    -------
    gpd.GeoDataFrame
        matches input dataframe with an additional boolean column: 'wallpoint' 
        
    """
    req = ["streamID", "xsID", "alpha", "slope", "curvature"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")

    # classify floor points and wall points on each profile
    processed_dfs = []
    grouped = xsections.groupby(['streamID', 'xsID'])
    ngroups = len(grouped)

    for i, ((streamID, xsID), profile) in enumerate(grouped):
        percent_complete = (i / total_groups) * 100
        if i % (ngroups // 100) == 0 or i == ngroups:  # Log at 1% steps or the last iteration
            logger.debug(f"Iteration {i} / {total_groups} ({percent_complete:.2f}% complete): Processing streamID={stream_id}, xsID={xs_id}")

        classified = profile.copy()
        classified['bp'] = False
        peaks = signal.find_peaks(-classified['curvature'], distance=distance, height=height)[0]
        classified.loc[profile.index[peaks], 'bp'] = True

        classified = classify_profile_slope_threshold(classified, slope_threshold)
        processed_dfs.append(classified)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df

def classify_profile_slope_threshold(profile, slope_threshold):
    """
    Splits the cross section profile and finds the wallpoint for each side 
    """
    profile['wallpoint'] = False

    pos, neg = split_profile(profile, duplicate_center=True)
    pos_wall_loc = _find_wall_half(pos, slope_threshold)
    neg_wall_loc = _find_wall_half(neg, slope_threshold)

    if pos_wall_loc is not None:
        profile.loc[pos_wall_loc, "wallpoint"] = True
    if neg_wall_loc is not None:
        profile.loc[neg_wall_loc, "wallpoint"] = True
    return profile

def _find_wall_half(half_profile, slope_threshold):
    """
    returns first upstream neighbor of the candidate point
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
