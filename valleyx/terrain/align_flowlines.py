"""
Workflow for aligning a flowlines to a flow accumulation raster.

Inputs:
    flowlines gpd.GeoDataFrame
    flow_acc rioxarray DataArray
    flow_dir rioxarray DataArray
    wbt (instance of whitebox.WhiteBoxTools class)

Outputs:
    flowpaths_identified rioxarray DataArray
    flowlines (gpd.GeoDataFrame)
"""
import os
import shutil
import sys
import warnings

import numpy as np
import networkx as nx
import geopandas as gpd
import xarray as xr
import rioxarray as rxr
import shapely
from shapely.geometry import Point

def flowlines2net(flowlines):
    """ assumes line.coords[0] is start of flowline and line.coords[-1] is end """
    G = nx.DiGraph()
    for line in flowlines.geometry:
        start = line.coords[0]
        end = line.coords[-1]
        G.add_edge(start, end)
    return G

def start_points(flowlines):
    graph = flowlines2net(flowlines)
    start_nodes = []
    for node in graph.nodes():
        if graph.in_degree(node) == 0: 
            start_nodes.append(Point(node))
    start_points = gpd.GeoSeries(start_nodes, crs=flowlines.crs)
    return start_points


def align_flowlines(flowlines, flow_acc, flow_dir, wbt):
    old_working_dir = wbt.work_dir
    new_working_dir = os.path.join(old_working_dir, "align_flowlines_temp/")

    os.makedirs(new_working_dir)

    files = {
            'seed_points': os.path.join(new_working_dir, 'sp.shp'),
            'snapped_seed_points': os.path.join(new_working_dir, 'snapped_sp.shp'),
            'flowpaths': os.path.join(new_working_dir, 'flowpaths.tif'),
            'flowpaths_id': os.path.join(new_working_dir, 'flowpaths_id.tif'),
            'flowlines': os.path.join(new_working_dir, 'flowlines.shp'),
            'flow_acc': os.path.join(new_working_dir, 'flow_acc.tif'),
            'flow_dir': os.path.join(new_working_dir, 'flow_dir.tif')}

    sps = start_points(flowlines)

    # save seed points
    sps.to_file(files['seed_points'])
    
    # save flow_acc and flow_dir
    flow_acc.rio.to_raster(files['flow_acc'])
    flow_dir.rio.to_raster(files['flow_dir'])

    wbt.snap_pour_points(
            files['seed_points'],
            files['flow_acc'],
            files['snapped_seed_points'],
            snap_dist = 50)

    wbt.trace_downslope_flowpaths(
            files['snapped_seed_points'],
            files['flow_dir'],
            files['flowpaths'],
            )

    wbt.stream_link_identifier(
            files['flow_dir'],
            files['flowpaths'],
            files['flowpaths_id'],
            )
    wbt.raster_streams_to_vector(
            files['flowpaths_id'],
            files['flow_dir'],
            files['flowlines'],
            )

    flowlines = gpd.read_file(files['flowlines'])
    flowlines = flowlines.set_crs(flow_acc.rio.crs)
    flowlines['geometry'] = flowlines['geometry'].apply(validate_flowline, args=(flow_acc,))

    flowlines = flowlines[['STRM_VAL', 'geometry']]
    flowlines = flowlines.sort_values('STRM_VAL')
    flowlines = flowlines.reset_index(drop=True)
    flowlines = flowlines.rename(columns = {'STRM_VAL': 'streamID'})

    flowpaths = rxr.open_rasterio(files['flowpaths_id'], masked=True).squeeze()

    unique_flowlines = flowlines['streamID'].unique()
    unique_flowpaths = np.unique(flowpaths.values)
    unique_flowpaths = unique_flowpaths[np.isfinite(unique_flowpaths)]

    if set(unique_flowlines) - set(unique_flowpaths):
        sys.exit("some flowlines not in flowpaths, something went wrong")
    #if set(unique_flowpaths) - set(unique_flowlines):
    #    warnings.warn("There are more flowpath ids then flowline ids, this is probably the result of the whiteboxtools raster_stream_to_vector method not creating a flowline in the case of a flowpath with a single cell")


    flowlines = gpd.GeoSeries(flowlines['geometry'].values, index=flowlines['streamID'], crs= flowpaths.rio.crs)

    wbt.set_working_dir(old_working_dir)
    shutil.rmtree(new_working_dir)
    return flowlines, flowpaths

def get_inlet_and_outlet_points(flowline, flow_acc):
    coords = gpd.GeoSeries([Point(flowline.coords[0]), Point(flowline.coords[-1])])
    xs = xr.DataArray(coords.geometry.x.values, dims='z')
    ys = xr.DataArray(coords.geometry.y.values, dims='z')
    fa = flow_acc.sel(x=xs, y=ys, method='nearest').values
    coords = coords.iloc[fa.argsort()]
    start = coords.iloc[0]
    end = coords.iloc[1]
    return start, end


def flowline_flows_downstream(flowline, flow_acc):
    start, end = get_inlet_and_outlet_points(flowline, flow_acc)
    if shapely.equals(start, Point(flowline.coords[0])) and shapely.equals(
        end, Point(flowline.coords[-1])
    ):
        return True
    else:
        return False


def validate_flowline(flowline, flow_acc):
    if flowline_flows_downstream(flowline, flow_acc):
        return flowline
    else:
        new_flowline = flowline.reverse()
        if flowline_flows_downstream(new_flowline, flow_acc):
            return new_flowline
        else:
            raise ValueError("Attempt to repair flowline failed")

def _validate_flowlines(flowlines, flow_acc):
    flowlines['geometry'] = flowlines['geometry'].apply(validate_flowline, args=(flow_acc,))
    return flowlines
