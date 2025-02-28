import numpy as np
import networkx as nx
import geopandas as gpd
import xarray as xr
from shapely.geometry import Point
import shapely

from valleyx.utils.raster import pixel_to_point
from valleyx.utils.raster import finite_unique


def pour_points_from_flowpaths(
    flow_paths: xr.DataArray, flow_acc: xr.DataArray
) -> gpd.GeoSeries:
    """
    Returns outlet cell for each stream
    where the outlet cell is the cell with the maximum flow accumulation value
    """
    pour_points_list = []

    for streamID in finite_unique(flow_paths):
        stream_mask = flow_paths == streamID
        fa_values = np.where(stream_mask, flow_acc.values, np.nan)
        max_idx = np.unravel_index(np.nanargmax(fa_values), fa_values.shape)
        row, col = max_idx
        pour_point = pixel_to_point(flow_paths, int(row), int(col))
        pour_points_list.append(pour_point)

    pour_points = gpd.GeoSeries(pour_points_list, crs=flow_paths.rio.crs)
    pour_points.index = finite_unique(flow_paths).tolist()
    return pour_points


def flowlines2net(flowlines):
    """convert flowlines to networkx graph"""
    G = nx.DiGraph()
    for streamID, line in flowlines.geometry:
        start = line.coords[0]
        end = line.coords[-1]
        G.add_edge(start, end, streamID=streamID)
    return G


def find_first_order_reaches(flowlines):
    """returns list of streamIDs of first order streams segments or reaches"""
    graph = flowlines2net(flowlines)
    source_nodes = [node for node in graph.nodes() if graph.in_degree(node) == 0]
    first_order = []
    for node in source_nodes:
        for edge in graph.edges(node, data=True):
            streamID = edge[2]["streamID"]
            first_order.append(streamID)
    return first_order


def find_channel_heads(flowlines):
    """get channel heads from flowlines"""
    graph = flowlines2net(flowlines)
    start_nodes = []
    for node in graph.nodes():
        if graph.in_degree(node) == 0:
            start_nodes.append(Point(node))
    start_points = gpd.GeoSeries(start_nodes, crs=flowlines.crs)
    return start_points


def prep_flowlines(flowlines, flow_acc):
    def get_inlet_and_outlet_points(flowline, flow_acc):
        """get the inlet and outlet points of a single flowline"""
        coords = gpd.GeoSeries([Point(flowline.coords[0]), Point(flowline.coords[-1])])
        xs = xr.DataArray(coords.geometry.x.values, dims="z")
        ys = xr.DataArray(coords.geometry.y.values, dims="z")
        fa = flow_acc.sel(x=xs, y=ys, method="nearest").values
        coords = coords.iloc[fa.argsort()]
        start = coords.iloc[0]
        end = coords.iloc[1]
        return start, end

    def flowline_flows_downstream(flowline, flow_acc):
        """check if flowline flows downstream"""
        start, end = get_inlet_and_outlet_points(flowline, flow_acc)
        if shapely.equals(start, Point(flowline.coords[0])) and shapely.equals(
            end, Point(flowline.coords[-1])
        ):
            return True
        else:
            return False

    def validate_flowline(flowline, flow_acc):
        """validate flowline direction"""
        if flowline_flows_downstream(flowline, flow_acc):
            return flowline
        else:
            new_flowline = flowline.reverse()
            if flowline_flows_downstream(new_flowline, flow_acc):
                return new_flowline
            else:
                raise ValueError("Attempt to repair flowline failed")

    flowlines["geometry"] = flowlines["geometry"].apply(
        validate_flowline, args=(flow_acc,)
    )
    flowlines = flowlines[["STRM_VAL", "geometry"]]
    flowlines = flowlines.sort_values("STRM_VAL")
    flowlines = flowlines.reset_index(drop=True)
    flowlines = flowlines.rename(columns={"STRM_VAL": "streamID"})
    flowlines = gpd.GeoSeries(
        flowlines["geometry"].values, index=flowlines["streamID"], crs=flow_acc.rio.crs
    )
    return flowlines
