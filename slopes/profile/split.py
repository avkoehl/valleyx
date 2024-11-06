import pandas as pd
import geopandas as gpd

def split_profile(profile, duplicate_center=False):
    pos = profile.loc[profile['alpha'] >= 0]

    if duplicate_center:
        neg = profile.loc[profile['alpha'] <= 0].copy()
    else:
        neg = profile.loc[profile['alpha'] < 0].copy()
    neg['alpha'] = neg['alpha'].abs()
    neg = neg.sort_values('alpha')
    return pos, neg

def combine_profile(pos: gpd.GeoDataFrame, neg: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Combine positive and negative sides of a profile into a single sorted DataFrame.
    
    Parameters
    ----------
    pos : gpd.GeoDataFrame
        Profile points with positive alpha values
    neg : gpd.GeoDataFrame
        Profile points with negative alpha values
        
    Returns
    -------
    gpd.GeoDataFrame
        Combined and sorted profile
    """
    neg['alpha'] = neg['alpha'] * -1
    return pd.concat([pos, neg]).sort_values('alpha')

