"""
This module identifies river reaches based on a valley width perspective.

Each reach, in this case, is a length of the river that has a relatively homogenous valley floor width.
Reaches are then optionally grouped together based on classifications of valley floor width:
    classes:
        median_width > 300 -> plain (e.g. alluvial valley, estuary, tectonically formed basin...)
        median_width > 100 -> unconfined
        median_width > 50  -> partly-confined 
        median_width <= 50 -> confined

Inputs are a valley floor polygon, valley floor polygon centerline, and the river's flowline

See centerline.py for how to get the centerline of a polygon
Valley floor polygon can be naively approximated by taking HAND <= 10m

steps:
    generate width series (width of lines perpendicular to centerline where they intersect the valley floor polygon bounds)
    find breakpoints in width series (change point detection algorithm)
    group segments (remove small segments, group into classes described above)

input:
    valley_floor (rough_out.py)
    centerline (valley_centerline.py)
    flowline

output:
    pour_points gpd.GeoSeries (points along the flowline that represent a break in the width series
"""
import geopandas as gpd
import numpy as np
import pandas as pd
import ruptures as rpt
from shapely.geometry import Point
from shapely.ops import nearest_points

from valleyx.geometry.width import polygon_widths

def segment_reaches(valley_floor, centerline, flowline, spacing, window, minsize):
    if centerline.length < minsize:
        return None

    widths = polygon_widths(valley_floor, centerline, spacing=spacing)
    if (len(widths) * spacing) < minsize:
        return None

    widths = _series_to_segments(widths, centerline, window=window, minsize=minsize)
    bp_inds = _change_point_inds(widths)

    if len(bp_inds) == 0:
        return None

    # get points along flowlines
    ppts = _pour_points(bp_inds, widths, flowline)
    return ppts

# -- internal
def _series_to_segments(widths, centerline, window, minsize):
    bp_inds = _breakpoint_inds(widths['width'], window=window)
    widths = _add_segment_id_column(bp_inds, widths)
    widths = _group_segments(widths)
    widths = _filter_small(widths, centerline, minsize=minsize)
    return widths

def _pour_points(bp_inds, widths, flowline):
    points = widths.iloc[bp_inds]
    nearest = [nearest_points(flowline, bp)[0] for bp in points['center_point']]
    # TODO: improve this to use the cross section line intersection first
    # if multipoint pick the point nearest to the center_point
    return gpd.GeoSeries(nearest, crs=widths.crs)

def _change_point_inds(widths):
    condition = widths['segment_id'].diff() != 0
    condition.iat[0] = False
    return np.where(condition)[0]

def _group_segments(width_series_df):
    # for each segment get median width
   def get_group(x):
       if x > 300:
           return 'plain'
       if x > 100:
           return 'unconfined'
       if x > 50:
           return 'partly-unconfined'
       else:
           return 'confined'

   segments = width_series_df[['segment_id', 'width']].groupby("segment_id").median()
   segments = segments.reset_index()
   segments['group'] = segments['width'].apply(get_group)

   to_drop = []
   for i, row in enumerate(segments.iterrows()):
      row = row[1]
      if i == len(segments) - 1:
          break

      current_group = row['group']
      next_group = segments.iloc[i+1]['group']
      if current_group == next_group:
         to_drop.append(row['segment_id'])

   df = _update_segment_id_column(width_series_df, to_drop)
   return df

def _breakpoint_inds(series, pen=10, window=5):
    signal = series.rolling(window=window, center=True).mean().fillna(series).values
    algo = rpt.Pelt(model='rbf').fit(signal)
    result = algo.predict(pen=pen)
    result = result[0:-1] # since last value is just the number of observations
    return result

def _add_segment_id_column(bp_inds, width_series_df):
    width_series_df['segment_id'] = -1
    
    current_segment = 1
    for i in range(width_series_df.shape[0]):
        if i in bp_inds:
            current_segment = current_segment + 1
        width_series_df['segment_id'].iat[i] = current_segment
    return width_series_df

def _update_segment_id_column(width_series_df, ids_to_remove):
    # if a segment is removed, all of its members are added to the next segment id
    # segment ids are renamed from 1 to number of segments
    new_df = width_series_df.copy()
    if isinstance(ids_to_remove, int):
        ids_to_remove = [ids_to_remove]
        
    for segment_id in ids_to_remove:
        unique_segments = new_df['segment_id'].dropna().unique()
        unique_segments = pd.Series(unique_segments).sort_values()

        if len(unique_segments) == 1:
            break

        if segment_id == unique_segments.iloc[-1]:
            # high to low
            htl = unique_segments.sort_values(ascending=False)
            to_attach = htl.iloc[np.argmax(htl < segment_id)]
            new_df.loc[new_df['segment_id'] == segment_id, "segment_id"] = to_attach

        else:
            to_attach = unique_segments.iloc[np.argmax(unique_segments > segment_id)]
            new_df.loc[new_df['segment_id'] == segment_id, "segment_id"] = to_attach

    # update segment_ids to be from 1 to nsegments
    for i,u in enumerate(new_df['segment_id'].unique()):
        new_df.loc[new_df['segment_id'] == u, "segment_id"] = i+1

    return new_df

def _segment_lengths(width_series_df, centerline):
    # for each segment get its length
    # true start point of any segment is the last point of the last segment
    lengths = []
    ids = []
    for segment_id in width_series_df['segment_id'].unique():
        rows = width_series_df.loc[width_series_df['segment_id'] == segment_id]
        if segment_id == 1:
            start = centerline.project(rows['center_point'].iloc[0])
            end = centerline.project(rows['center_point'].iloc[-1])
            lengths.append(end-start)
            ids.append(segment_id)
        else:
            start = centerline.project(width_series_df.loc[width_series_df['segment_id'] == (segment_id -1)].iloc[-1]['center_point'])
            end = centerline.project(rows['center_point'].iloc[-1])
            lengths.append(end-start)
            ids.append(segment_id)
    
    sdf = pd.DataFrame({'segment_id': ids, 'length': lengths})
    return sdf

def _cascade_filter_id_segments(sdf, minsize):
    remove_segments = []
    new_values = []
    to_add = 0
    value = 0
    
    for _, row in sdf.iterrows():
        value = row['length']
        value = value + to_add
    
        if value < minsize:
            remove_segments.append(row['segment_id'])
            to_add = value
        else:
            to_add = 0
            new_values.append(value)
    
    if to_add > 0:
        new_values.append(value)
    return remove_segments
    
def _filter_small(width_series_df, centerline, minsize):
    sdf = _segment_lengths(width_series_df, centerline)
    to_remove = _cascade_filter_id_segments(sdf, minsize)
    df = _update_segment_id_column(width_series_df, to_remove)
    return df
