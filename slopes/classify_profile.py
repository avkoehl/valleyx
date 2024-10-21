import pandas as pd
import geopandas as gpd
import numpy as np


def classify_profiles(xsections: gpd.GeoDataFrame, method = 'slope_threshold', slope_threshold=12.5) -> gpd.GeoDataFrame: 
    """
    add two columns: wall_point, floor
    """
    req = ["streamID", "xsID", "alpha", "slope", "label", "bp"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")

    # classify floor points and wall points on each profile
    processed_dfs = []
    for (streamID, xsID), profile in xsections.groupby(['streamID', 'xsID']):

        if method == "slope_threshold":
            classified = classify_profile_slope_threshold(profile, slope_threshold)
        elif method == "delta_slope_threshold":
            baseline_slope = profile.loc[profile['alpha'] == 0, 'slope'].item()
            classified = classify_profile_slope_threshold(profile, baseline_slope)
        elif method == "max_ascent":
            raise ValueError("max ascent not implemented yet")
        else:
            raise ValueError("method doesn't exist")

        processed_dfs.append(classified)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df

def classify_profile_slope_threshold(profile, slope_threshold):
    profile['floor'] = False
    profile['wallpoint'] = False

    slopes = profile.groupby("label")['slope'].median()
    center_label = profile.loc[profile['alpha'] == 0, 'label'].item()

    if slopes.loc[center_label] > slope_threshold:
        center_iloc = np.argmax([profile['alpha'] == 0])
        profile.loc[profile['alpha'] == 0, "floor"] = True
        neighbor_indexes = [profile.index[center_iloc - 1], profile.index[center_iloc + 1]]
        profile.loc[neighbor_indexes, "wallpoint"] = True
        return profile
    else:
        profile.loc[profile['label'] == center_label, 'floor'] = True
        # up
        for label in range(center_label, profile['label'].max()+1):
            # add to floors
            if slopes.loc[label] <= slope_threshold:
                profile.loc[profile['label'] == label, 'floor'] = True
            else:
            # break, wall point is the point with that label and smalles abs(alpha)
                label_alphas = profile.loc[profile['label'] == label, 'alpha']
                wall_point_1_loc = label_alphas.index[np.argmin(label_alphas.abs())]
                profile.loc[wall_point_1_loc, 'wallpoint'] = True
                break

        # down
        for label in range(center_label, -1, -1):
            if slopes.loc[label] <= slope_threshold:
                profile.loc[profile['label'] == label, 'floor'] = True
            else:
            # break, wall point is the point with that label and smalles abs(alpha)
                label_alphas = profile.loc[profile['label'] == label, 'alpha']
                wall_point_2_loc = label_alphas.index[np.argmin(label_alphas.abs())]
                profile.loc[wall_point_2_loc, 'wallpoint'] = True
                break
        return profile
    return profile

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
