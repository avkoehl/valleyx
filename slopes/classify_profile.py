import pandas as pd
import geopandas as gpd
import numpy as np


def classify_profiles(xsections: gpd.GeoDataFrame, slope_threshold=12.5) -> gpd.GeoDataFrame: 
    """
    add two columns: wall_point, floor
    """
    req = ["streamID", "xsID", "alpha", "slope", "label", "bp"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")


    # preprocess each profile in the dataframe
    processed_dfs = []
    for (streamID, xsID), profile in xsections.groupby(['streamID', 'xsID']):
        
        profile['floor'] = False
        profile['wallpoint'] = False

        slopes = profile.groupby("label")['slope'].median()
        center_label = profile.loc[profile['alpha'] == 0, 'label'].item()

        if slopes.loc[center_label] > slope_threshold:
            continue
        else:
            floor_labels.append(center_label)
            # up
            for label in range(center_label, profile['label'].max()+1):
                # add to floors
                if slopes.loc[label] <= slope_threshold:
                    profile.loc[profile['label'] == label, 'floor'] = True
                else:
                # break, wall point is the point with that label and smalles abs(alpha)
                    label_alphas = profile.loc[profile['label'] == label, 'alpha']
                    wall_point_1_loc = label_alphas.index[label_alphas.abs.min()]
                    profile.loc[wall_point_1_loc, 'wallpoint'] = True
                    break

            # down
            for label in range(center_label, -1, -1):
                if slopes.loc[label] <= slope_threshold:
                    profile.loc[profile['label'] == label, 'floor'] = True
                else:
                # break, wall point is the point with that label and smalles abs(alpha)
                    label_alphas = profile.loc[profile['label'] == label, 'alpha']
                    wall_point_2_loc = label_alphas.index[label_alphas.abs.min()]
                    profile.loc[wall_point_2_loc, 'wallpoint'] = True
                    break


        processed_dfs.append(profile)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df
