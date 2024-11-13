from typing import Optional

import geopandas as gpd
import pandas as pd
import numpy as np
from scipy import signal

from valleyx.profile.split import split_profile
from valleyx.profile.split import combine_profile

def preprocess_profiles(
    xsections: gpd.GeoDataFrame,
    min_hand_jump: float,
    ratio: float,
    min_distance: float,
    min_peak_prominence: float,
) -> gpd.GeoDataFrame:
    """
    Preprocess cross-sectional profiles to prepare them for valley wall detection.
    
    This function applies several preprocessing steps to each profile in the cross-sections
    dataset to ensure the data is properly centered on the stream and does not include
    adjacent valleys.
    
    Preprocessing steps:
    1. Removes duplicated points that may arise from cell resolution issues
    2. Recenters profiles on the actual stream location
    3. Filters profiles to remove potential ridge crossings into adjacent valleys
    4. Ensures there are no large gaps in the profile points
    
    Parameters
    ----------
    xsections : gpd.GeoDataFrame
        Cross-sectional data with required columns:
        - geom : Point, points along the cross-section profile
        - pointID : numeric, unique identifier for each point
        - streamID : numeric, identifier for the flow line
        - xsID : numeric, cross-section identifier specific to the flowline
        - alpha : numeric, straight-line distance from center point
        - flow_path : numeric, streamID if point is stream, else np.nan
        - hillslope : numeric, hillslope identifier
        - conditioned_dem : numeric, elevation values
        - hand : numeric, height above nearest drainage
    min_hand_jump : float 
        Minimum height above drainage change to consider as potential valley crossing,
    ratio : float 
        Threshold ratio of HAND change to elevation change for detecting ridges,
    min_peak_prominence: float
        Prominence of peaks for scipy peak detection on elevation profile
    min_distance : float
        Minimum required distance from stream center in meters
    
    Returns
    -------
    gpd.GeoDataFrame
        Preprocessed cross-sections with invalid profiles removed and remaining
        profiles properly centered and bounded
    
    Raises
    ------
    ValueError
        If any required columns are missing from input DataFrame
    """
    # Validate required columns
    req = ["streamID", "xsID", "alpha", "flow_path", "hillslope", "conditioned_dem", "hand"]
    missing = [col for col in req if col not in xsections.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # Process each profile
    processed_dfs = []
    for (streamID, xsID), profile in xsections.groupby(['streamID', 'xsID']):
        # Apply preprocessing steps
        profile = _remove_duplicates(profile)
        profile = _recenter_on_stream(profile)
        profile = profile[~np.isnan(profile['conditioned_dem'])]
        
        # Skip profiles that don't extend far enough from stream
        if profile['alpha'].min() > -min_distance or profile['alpha'].max() < min_distance:
            continue
            
        profile = _filter_ridge_crossing(profile, min_hand_jump, ratio)

        # Apply peak-based filtering if prominence threshold is provided
        if min_peak_prominence is not None:
            profile = _filter_by_peaks(profile, min_peak_prominence)
        
        profile = _ensure_no_gaps(profile)
        
        # Recheck distance requirements after processing
        if profile['alpha'].min() > -min_distance or profile['alpha'].max() < min_distance:
            continue
            
        processed_dfs.append(profile)

    return gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))

def _filter_by_peaks(profile: gpd.GeoDataFrame, min_prominence: float) -> gpd.GeoDataFrame:
    """
    Filter profile based on significant peaks in elevation on either side of the stream.
    
    This function:
    1. Splits the profile into positive and negative alpha sections
    2. Finds peaks in elevation that meet the minimum prominence threshold
    3. Truncates each side at the first significant peak if found
    4. Returns original profile if no significant peaks are found
    
    Parameters
    ----------
    profile : gpd.GeoDataFrame
        Single cross-section profile
    min_prominence : float
        Minimum prominence (vertical distance between peak and lowest contour line)
        required for a peak to be considered significant
        
    Returns
    -------
    gpd.GeoDataFrame
        Profile truncated at first significant peaks if found, otherwise unchanged
    """
    def find_first_peak(profile, min_prominence):
        # Find peaks that meet prominence threshold
        peaks, properties = signal.find_peaks(profile['conditioned_dem'], prominence=min_prominence)
        
        if len(peaks) > 0:
            first_peak = peaks[0]
            return profile.iloc[0:first_peak]
        else:
            return profile
        
    
    # Split profile into positive and negative alpha sections
    pos, neg = split_profile(profile)
    
    # Process positive side
    if not pos.empty:
        pos = find_first_peak(pos, min_prominence)
    if not neg.empty:
        neg = find_first_peak(neg, min_prominence)
   
    # Combine filtered sides
    return combine_profile(pos, neg)

def _remove_duplicates(profile: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Remove duplicate points in the profile based on all columns except geometry and metadata.
    
    Parameters
    ----------
    profile : gpd.GeoDataFrame
        Single cross-section profile
        
    Returns
    -------
    gpd.GeoDataFrame
        Profile with duplicate points removed
    """
    ignore = ['geom', 'alpha', 'pointID']
    cols = [col for col in profile.columns if col not in ignore]
    return profile[~profile.duplicated(subset=cols, keep='first')]

def _recenter_on_stream(profile: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Recenter the profile on the actual stream location.
    
    When cross-sections are created perpendicular to a smoothed/simplified flowline,
    the center point (alpha == 0) may not align with the actual stream location.
    This function recenters the profile by:
    1. Looking for points marked as stream in flow_path
    2. If multiple stream points exist, selecting the one closest to alpha=0
    3. If no stream points, using hillslope boundary changes to estimate location
    
    Parameters
    ----------
    profile : gpd.GeoDataFrame
        Single cross-section profile
        
    Returns
    -------
    gpd.GeoDataFrame
        Profile recentered on the stream location
    """
    profile = profile.copy()
    streamID = profile['streamID'].iloc[0]
    fp_points = profile['flow_path'] == streamID
    
    # Find calibration point
    calibration_alpha = None
    
    # Case 1: Point(s) marked as stream exist
    if fp_points.sum():
        if fp_points.sum() == 1:
            calibration_alpha = profile.loc[fp_points, 'alpha'].iloc[0]
        else:
            points = profile.loc[fp_points]
            sorted_points = points.sort_values(
                by=['hand', 'alpha'],
                key=lambda col: col.abs() if col.name == 'alpha' else col
            )
            calibration_alpha = sorted_points['alpha'].iloc[0]
    
    # Case 2: Use hillslope boundary changes
    else:
        hs_changes = pd.concat([
            profile.loc[profile['hillslope'].shift() != profile['hillslope']],
            profile.loc[profile['hillslope'].shift(-1) != profile['hillslope']]
        ])
        hs_changes = hs_changes[~hs_changes['pointID'].duplicated(keep='first')]
        if not hs_changes.empty:
            calibration_alpha = hs_changes['alpha'].sort_values(key=abs).iloc[0]
    
    # Apply recentering if calibration point found
    if calibration_alpha is not None:
        profile['alpha'] = profile['alpha'] - calibration_alpha
        
    return profile

def _filter_ridge_crossing(
    profile: gpd.GeoDataFrame,
    min_hand_jump: float,
    ratio: float
) -> gpd.GeoDataFrame:
    """
    Filter profile to remove points beyond ridge crossings into adjacent valleys.
    
    Identifies potential ridge crossings by looking for locations where the rate
    of change in height above drainage (HAND) is significantly larger than the
    rate of change in elevation.
    
    Parameters
    ----------
    profile : gpd.GeoDataFrame
        Single cross-section profile
    min_hand_jump : float
        Minimum HAND value to consider as potential valley crossing
    ratio : float
        Threshold ratio of HAND change to elevation change
        
    Returns
    -------
    gpd.GeoDataFrame
        Profile truncated at ridge crossings if found
    """
    def _filter_ratio(hand: pd.Series, elevation: pd.Series, ratio: float, min_jump: float) -> pd.Index:
        """Helper function to identify ridge crossing points"""
        ratio_series = hand.diff().fillna(0.001) / elevation.diff().fillna(0.001)
        ratio_series = ratio_series.abs()
        condition = (ratio_series > ratio) & (hand > min_jump)
        position = condition.argmax()
        return hand.index[:position] if position != 0 else hand.index
    
    # Split profile into positive and negative alpha sections
    pos, neg = split_profile(profile)
    
    # Filter each side independently
    pos = pos.loc[_filter_ratio(pos['hand'], pos['conditioned_dem'], ratio, min_hand_jump)]
    neg = neg.loc[_filter_ratio(neg['hand'], neg['conditioned_dem'], ratio, min_hand_jump)]
    
    return combine_profile(pos, neg)

def _ensure_no_gaps(profile: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Filter profile to remove sections with large gaps between points.
    
    Parameters
    ----------
    profile : gpd.GeoDataFrame
        Single cross-section profile
        
    Returns
    -------
    gpd.GeoDataFrame
        Profile with large gaps removed
    """
    def _filter_max_increment(series: pd.Series, max_increment: float) -> pd.Series:
        """Helper function to identify points before large gaps"""
        diff = series.diff().fillna(0)
        exceed = diff[diff > max_increment]
        if not exceed.empty:
            position = diff.index.get_loc(exceed.idxmin())
            return series.iloc[:position]
        return series
    
    # Calculate maximum allowed gap as 3x the most common point spacing
    max_increment = profile['alpha'].diff().mode().iloc[0] * 3
    
    # Split and filter each side independently
    pos, neg = split_profile(profile)
    pos = pos.loc[_filter_max_increment(pos['alpha'], max_increment).index]
    neg = neg.loc[_filter_max_increment(neg['alpha'], max_increment).index]
    
    return combine_profile(pos, neg)
