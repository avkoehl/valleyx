"""
Transition zones

Move along cross section find the point that maximizes the outer/inner slope mean ratio

input:
    profile
    max_hand
"""

import pandas as pd
import geopandas as gpd
from tqdm import tqdm

from valleyx.profile.split import split_profile
from valleyx.profile.split import combine_profile

def classify_transition_zone(xsections, max_hand, min_ratio):
    req = ["streamID", "xsID", "alpha", "slope", "curvature", "hand"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")

    # classify floor points and wall points on each profile
    processed_dfs = []
    for (streamID, xsID), profile in tqdm(xsections.groupby(['streamID', 'xsID'])):
        classified = profile.copy()
        classified = find_wallpoints_tz(classified, max_hand, min_ratio)
        processed_dfs.append(classified)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df


def find_wallpoints_tz(profile, max_hand, min_ratio):
    profile['wallpoint'] = False
    # 1. split
    pos, neg = split_profile(profile)

    pos_wall_loc = find_wall_point_tz_half(pos, max_hand, min_ratio)
    neg_wall_loc = find_wall_point_tz_half(neg, max_hand, min_ratio)

    if pos_wall_loc is not None:
        profile.loc[pos_wall_loc, "wallpoint"] = True
    if neg_wall_loc is not None:
        profile.loc[neg_wall_loc, "wallpoint"] = True
    return profile

    # 
def find_wall_point_tz_half(half_profile, max_hand, min_ratio):
    candidates = half_profile.loc[(half_profile['curvature'] < 0)
                                  & (half_profile['hand'] < max_hand)
                                  ].copy()

    if not len(candidates):
        return None

    ratios = []
    for idx in candidates.index:
        dist = half_profile.loc[idx, 'alpha']

        inner_mask = half_profile['alpha'] <= dist
        outer_mask = half_profile['alpha'] > dist

        inner_mean = half_profile.loc[inner_mask, 'slope'].mean()
        outer_mean = half_profile.loc[outer_mask, 'slope'].mean()

        ratio = outer_mean / inner_mean
        ratios.append(ratio)

    candidates['slope_ratio'] = ratios
    max_ratio = candidates['slope_ratio'].max()
    max_ratio_idx = candidates['slope_ratio'].idxmax()

    if max_ratio < min_ratio:
        return None
    else:
        return max_ratio_idx
