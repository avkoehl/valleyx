import argparse
import os
import shutil

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPoint
from shapely.geometry import Point
from shapely.ops import snap
from shapely.ops import split
from rioxarray.merge import merge_arrays
import xarray as xr
from loguru import logger

from slopes.geometry.centerline import polygon_centerline
from slopes.reach.rough_out import rough_out_hand
from slopes.reach.reach import segment_reaches
from slopes.utils import translate_to_wbt
from slopes.terrain.subbasins import label_subbasins_pour_points
from slopes.terrain.hillslopes import wbt_label_drainage_sides

logger.disable("slopes")

def delineate_reaches(dataset, flowlines, wbt, num_points, spacing, minsize, window):
    logger.info("Rough out valley floors")
    vfs = rough_out_hand(dataset['subbasin'], dataset['hand'], 10)
    logger.info("Segment into reaches")
    result = reach_subbasins(vfs, dataset['flow_path'], flowlines, 
                             dataset['flow_acc'], dataset['flow_dir'], 
                             wbt, num_points, spacing, minsize, window)

    dataset['flow_path'] = result['flowpaths_reaches']
    dataset['subbasin'] = result['subbasins']
    dataset['hillslope'] = result['hillslopes']
    return dataset, result['flowlines_reaches']

def reach_subbasins(valley_floors, flowpaths, flowlines, flow_acc, flow_dir, wbt, num_points, spacing, minsize, window):
    logger.info("get points that represent the breaks")
    fpcells, flowline_points, flowpath_points = _compute_reaches(valley_floors, flowpaths, flowlines, flow_acc, num_points, spacing, minsize, window)
    logger.info("relabel things")
    flowpaths_reaches = _relabel_flowpaths(fpcells, flowpaths)
    flowlines_reaches = flowpath_to_flowlines(flowpaths_reaches, flow_dir, wbt)
    flowlines_reaches = flowlines_reaches.rename(columns={'STRM_VAL':'streamID'})
    flowlines_reaches = flowlines_reaches[['streamID', 'geometry']]
    flowlines_reaches = flowlines_reaches.sort_values(by='streamID')
    reaches = gpd.GeoSeries(flowlines_reaches['geometry'])
    reaches.index = flowlines_reaches['streamID']
    reaches.crs = flowpaths.rio.crs
    flowlines_reaches = reaches
    logger.info("compute subbasins and hillslopes")
    subbasins = _reach_subbasins(flowpath_points, flowpaths_reaches, flow_dir, wbt)
    hillslopes = _reach_hillslopes(subbasins, flowpaths_reaches, flow_dir, wbt)
    return {
            'flowpaths_reaches': flowpaths_reaches,
            'flowlines_reaches': flowlines_reaches,
            'subbasins': subbasins,
            'hillslopes': hillslopes}

def _compute_reaches(valley_floors, flowpaths, flowlines, flow_acc, num_points, spacing, minsize, window):
    all_flowpath_cells = gpd.GeoDataFrame()
    all_points = gpd.GeoDataFrame()
    all_points_snapped = gpd.GeoDataFrame()
    count = 0 
    for ID, valley_floor in valley_floors.items():
        count += 1
        percent = round(count/len(valley_floors) * 100, 2)
        logger.info(f"Splitting {ID} into reaches, {count}/{len(valley_floors)} {percent}%")
        if ID not in flowlines.index.values:
            continue
        flowpath = flowpaths.where(flowpaths == ID, drop=False)
        flowline = flowlines.loc[ID]
    
        source = Point(flowline.coords[0])
        target = Point(flowline.coords[-1])
        centerline = polygon_centerline(valley_floor, num_points=num_points, source=source, target=target, simplify_tolerance = 5, dist_tolerance = 100, smooth_output=True)

        flowpath_cells = _flowpath_cells(flowpath, flow_acc)

        points = segment_reaches(valley_floor, centerline, flowline, spacing, minsize, window)

        if points is not None:
            snapped_points = _snap_to_flowpath(points, flowpath_cells)
            snapped_points = pd.concat([snapped_points, flowpath_cells.iloc[[-1]]], ignore_index=True)
            points = pd.concat([points, gpd.GeoSeries(target)], ignore_index=True)
        else:
            snapped_points = flowpath_cells.iloc[[-1]]
            points = gpd.GeoSeries(target, crs=flow_acc.rio.crs)

        flowpath_cells = _assign_reach_id(flowpath_cells, snapped_points['cell_id'])
        all_flowpath_cells = pd.concat([all_flowpath_cells, flowpath_cells], ignore_index=True)
        all_points_snapped = pd.concat([all_points_snapped, snapped_points], ignore_index=True)
    
        points_df = gpd.GeoDataFrame(points, columns=['geometry'], crs=flowlines.crs)
        points_df['segment_id'] = ID
        all_points = pd.concat([all_points, points_df], ignore_index=True)
    return all_flowpath_cells, all_points, all_points_snapped

def _relabel_flowpaths(flowpath_cells, flowpaths):
    # relabel flowpaths
    new_fp = flowpaths.copy()
    flowpath_cells['label'] = (flowpath_cells['segment_id'] * 100 + flowpath_cells['reach_id']).astype(int)
    for label, inds in flowpath_cells.groupby('label').groups.items():
        rows = flowpath_cells['row'].loc[inds].values
        cols = flowpath_cells['col'].loc[inds].values
        new_fp.values[rows,cols] = label
    return new_fp

def _reach_subbasins(flowpath_points, flowpaths, flow_dir, wbt):
    whitebox_aligned = translate_to_wbt(flowpath_points, flowpaths.rio.resolution())
    subbasins = label_subbasins_pour_points(flow_dir, whitebox_aligned, wbt)
    copy = subbasins.copy()
    
    # relabel subbasins
    for sid in np.unique(subbasins):
        if not np.isnan(sid):
           condition = (subbasins == sid)
           fp = flowpaths.where(condition)
           values = fp.values[np.isfinite(fp.values)]
           value = np.unique(values).item()
           copy.data[condition] = int(value)
    return copy

def _reach_hillslopes(subbasins, flowpaths, flowdir, wbt):
    hillslopes = subbasins.copy()
    hillslopes.data = np.full(subbasins.shape, np.nan, dtype=subbasins.dtype)
    for sid in np.unique(subbasins):
        if np.isfinite(sid):
            condition = (subbasins == sid)
            fp = flowpaths.where(condition)
            fd = flowdir.where(condition)
            hs = wbt_label_drainage_sides(fd, fp, wbt)
            hillslopes = xr.where(hillslopes.isnull(), hs, hillslopes)
    return hillslopes
   
def _snap_to_flowpath(points, flowpath_cells):
    """
    points gpd.GeoSeries
    return
       gdp.GeoDataFrame points row, col, cell_id, geometry
    """
    matched_points = []

    locs = []
    for point in points:
        dists = flowpath_cells.distance(point)
        locs.append(dists.idxmin())

    return flowpath_cells.loc[locs]

def _flowpath_cells(flowpath_mask, flowacc):
    """
    for each cell in flowpath get the flow accumulation, its id, its coordinate, its x, its y
    sort by flowacc
    """
    condition = np.isfinite(flowpath_mask)

    id_grid = np.arange(flowpath_mask.size).reshape(flowpath_mask.shape)
    stream_points = id_grid[condition]
    fa_values = flowacc.data[condition]
    rows, cols = np.where(condition)
    # notice y,x are swapped. not sure if this is always the case with the rasterarrays, but don't want to think about it too much right now
    coordinates = [Point(condition.rio.transform() * (y,x)) for x,y in zip(rows, cols)]

    df = gpd.GeoDataFrame({
            'segment_id': np.unique(flowpath_mask.data[condition]).item(),
            'cell_id': stream_points,
            'flow_acc': fa_values,
            'geometry': coordinates,
            'row': rows,
            'col': cols}, geometry='geometry', crs=flowpath_mask.rio.crs)

    return df.sort_values('flow_acc')

def _assign_reach_id(flowpath_cells, bp_cell_ids):
    reach_ids = []
    reach = 0
    for cell_id in flowpath_cells['cell_id']:
        reach_ids.append(reach)
        if cell_id in bp_cell_ids.values:
            reach += 1

    flowpath_cells['reach_id'] = reach_ids
    return flowpath_cells

def flowpath_to_flowlines(flowpath, flowdir, wbt):
    work_dir = wbt.work_dir
    files = {
            'temp_flowpath': os.path.join(work_dir, 'temp_flowpath.tif'),
            'temp_flowdir': os.path.join(work_dir, 'temp_flowdir.tif'),
            'flowlines': os.path.join(work_dir, 'flowlines.shp')}

    flowpath.rio.to_raster(files['temp_flowpath'])
    flowdir.rio.to_raster(files['temp_flowdir'])

    wbt.raster_streams_to_vector(
            files['temp_flowpath'],
            files['temp_flowdir'],
            files['flowlines'],)

    os.remove(files['temp_flowpath'])
    os.remove(files['temp_flowdir'])

    flowlines = gpd.read_file(files['flowlines'])
    return flowlines