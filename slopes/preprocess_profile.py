import geopandas as gpd
import pandas as pd

def preprocess_profiles(xsections: gpd.GeoDataFrame, min_hand_jump=15, ratio=2.5, min_distance=20) -> gpd.GeoDataFrame:
    """
    Applies preprocessing to each profile in a xsections dataframe.
    See
    Preprocessing steps:
    1. remove duplicated points 
    2. recenter on the stream
    3. filter for ridge crossing

    Parameters
    ----------
    xsections: gpd.GeoDataFrame
        A geodataframe with the following columns (see network_xsection):
        - "geom": Point, a point along the xsection profile
        - "pointID": numeric, unique point ID
        - "streamID": numeric, flow line id
        - "xsID": numeric, cross section id specific to the flowline
        - "alpha": numeric, represents the straight line distance from the
                   center point of the cross section

        And the following columns (see observe_values):
        - "flow_path": numeric, np.nan if not stream else streamID
        - "hillslope": numeric, id of the hillslope
        - "dem": numeric, elevation
        - "hand": numeric, height above nearest stream
	min_hand_jump: int
    ratio: int

    Returns
    -------
    gpd.GeoDataframe
        A geodataframe where the profiles have been preprocessed
    """

    # check for required columns:
    req = ["streamID", "xsID", "alpha", "flow_path", "hillslope", "dem", "hand"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")


    # preprocess each profile in the dataframe
    processed_dfs = []
    for (streamID, xsID), profile in xsections.groupby(['streamID', 'xsID']):
        profile = _remove_duplicates(profile)
        profile = _recenter_on_stream(profile)

        if profile['alpha'].min() > -min_distance or profile['alpha'].max() < min_distance:
            continue

        profile = _filter_ridge_crossing(profile, min_hand_jump, ratio)
        profile = _ensure_no_gaps(profile)
 

        # confirm atleast 20 meters worth of points on either side
        # if not don't append
        if profile['alpha'].min() > -min_distance or profile['alpha'].max() < min_distance:
            continue

        processed_dfs.append(profile)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df

def _remove_duplicates(profile: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    If the point spacing is less than the resolution of a cell can result in this
    """
    ignore = ['geom', 'alpha', 'pointID']
    cols = [col for col in profile.columns if col not in ignore]
    dup = profile.duplicated(subset=cols, keep='first')
    profile = profile[~dup]
    return profile

def _recenter_on_stream(profile: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """ 
    If the cross sections were created perpendicular to a smoothed/simplified
    version of the flowline LineString, then the center point (alpha == 0) may
    not be the actual flow path point. 

    This function attempts to recenter the profile onto the stream point -
    finds the stream point and recalibrates the alpha values around that point.
    If it doesn't work, will not alter the profile.

    To find the stream point - 
    1. 
    check if any profile['flowpath'] is equal to streamID
    if one place -> thats the center
    if more than one -> pick one closest to alpha == 0

    2.
    if none:
    find the places where the hillslope column changes value
    pick one closest to alpha == 0

    required: flow_path, hillslope 
    """

    streamID = profile['streamID'].iloc[0].item()
    fp_points = profile['flow_path'] == streamID

    calibration_alpha = None

    if fp_points.sum():
        if fp_points.sum() == 1:
            calibration_alpha = profile['alpha'].loc[fp_points].iloc[0].item()
        else:
            points = profile.loc[fp_points]
            sorted_points = points.sort_values(by=['hand', 'alpha'], key=lambda col: col.abs() if col.name == 'alpha' else col )
            calibration_alpha = sorted_points['alpha'].iloc[0].item()
    else:
        hs_change_points_down = profile.loc[profile['hillslope'].shift() != profile['hillslope']]
        hs_change_points_up = profile.loc[profile['hillslope'].shift(-1) != profile['hillslope']]
        hs_change_points = pd.concat([hs_change_points_down, hs_change_points_up])
        hs_change_points = hs_change_points[~hs_change_points['pointID'].duplicated(keep='first')]
        calibration_alpha = hs_change_points['alpha'].sort_values(key=abs).iloc[0].item()

    if calibration_alpha is None:
        # TODO: log
        return profile
    else:
        profile['alpha'] = profile['alpha'] - calibration_alpha
        return profile

def _filter_ridge_crossing(profile, min_hand_jump, ratio):
    # check for big jumps in HAND that arent matched by a jump in elevation
    def _filter_ratio(hand, elevation, ratio, min_jump):
        # find integer position where hand > 15 and hand/elevation > 3
        ratio_series = hand.diff().fillna(0.001) / elevation.diff().fillna(0.001)
        ratio_series = ratio_series.abs()
        condition = ((ratio_series > ratio) & (hand > min_jump))
        position = condition.argmax().item()
        if position != 0:
            return hand.index[:position]
        return hand.index

    pos, neg = _split_profile(profile)
    pos = pos.loc[_filter_ratio(pos['hand'], pos['dem'], ratio, min_hand_jump)]
    neg = neg.loc[_filter_ratio(neg['hand'], neg['dem'], ratio, min_hand_jump)]
    return _combine_profile(pos, neg)

def _split_profile(profile):
    pos = profile.loc[profile['alpha'] >= 0]
    neg = profile.loc[profile['alpha'] < 0].copy()
    neg['alpha'] = neg['alpha'].abs()
    neg = neg.sort_values('alpha')
    return pos, neg

def _combine_profile(pos, neg):
    neg['alpha'] = neg['alpha'] * - 1
    profile = pd.concat([pos, neg])
    profile = profile.sort_values('alpha')
    return profile


def _ensure_no_gaps(profile):
    def _filter_max_increment(series, max_increment):
        diff = series.diff().fillna(0)
        exceed = diff[diff > max_increment]
        if not exceed.empty:
            position = diff.index.get_loc(exceed.idxmin())
            return series.iloc[:position]
        return series

    max_increment = profile['alpha'].diff().mode().iloc[0] * 3
    pos, neg = _split_profile(profile)

    pos = pos.loc[_filter_max_increment(pos['alpha'], max_increment).index]
    neg = neg.loc[_filter_max_increment(neg['alpha'], max_increment).index]

    return _combine_profile(pos, neg)
