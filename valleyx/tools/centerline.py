"""
Function to get centerline of a valley polygon

Ensures that the start and end of the centerline are near the start and end of the stream line

1. get points equally dispersed on polygon border
2. create voronoi diagram for those points, clip to interior of polygon
3. find path along that diagram that is longest and most straight

https://observablehq.com/@veltman/centerline-labeling

Alternatively could try skeletonization or the method introduced in
https://esurf.copernicus.org/articles/10/437/2022/
"""

import itertools

import geopandas as gpd
import networkx as nx
import shapely
import pandas as pd
from shapely.geometry import Point, Polygon, LineString
from shapelysmooth import taubin_smooth  # prefer taubin unless need to preserve nodes
from shapelysmooth import chaikin_smooth

from valleyx.utils.geometry import create_points_along_boundary


def polygon_centerline(
    polygon,
    num_points,
    source=None,
    target=None,
    simplify_tolerance=None,
    dist_tolerance=None,
    smooth_output=True,
) -> LineString:
    """
    generic method for getting centerline of a polygon
    WARNING will take a long time to run even with modest number of points (e.g 50)
    recommend https://github.com/ungarj/label_centerlines
    """
    if simplify_tolerance > 0:
        polygon = polygon.simplify(simplify_tolerance)

    if dist_tolerance is not None:
        while True:
            points = create_points_along_boundary(polygon, num_points)
            simple = Polygon(points).buffer(0)  # helps ensure valid

            voronoi_graph = interior_voronoi(simple)
            bn = boundary_nodes(voronoi_graph)

            # set max num_points
            if num_points > 11999:
                break

            if source is not None:
                bn["distance_to_source"] = bn.distance(source)
                if (bn["distance_to_source"] < dist_tolerance).sum() == 0:
                    num_points *= 2
                    continue
            if target is not None:
                bn["distance_to_target"] = bn.distance(target)
                if (bn["distance_to_target"] < dist_tolerance).sum() == 0:
                    num_points *= 2
                    continue

            break
    else:
        points = create_points_along_boundary(polygon, num_points)
        simple = Polygon(points).buffer(0)  # helps ensure valid

        voronoi_graph = interior_voronoi(simple)
        bn = boundary_nodes(voronoi_graph)

    if source is not None:
        bn["distance_to_source"] = bn.distance(source)
        sources = bn.sort_values(by="distance_to_source", inplace=False)
        sources = sources.iloc[[0]]

    if target is not None:
        bn["distance_to_target"] = bn.distance(target)
        targets = bn.sort_values(by="distance_to_target", inplace=False)
        targets = targets.iloc[[0]]

    # edge case
    if source is not None and target is not None:
        if set(sources["node_id"]).intersection(set(targets["node_id"])):
            # raise ValueError("the source points and target points have overlap; they must be close to the same boundary segments")
            return None

    path = find_best_path(voronoi_graph, sources, targets)

    if smooth_output:
        return chaikin_smooth(taubin_smooth(path))
    else:
        return path


def interior_voronoi(polygon):
    # get voronoi
    voronoi = shapely.voronoi_polygons(polygon, only_edges=True)
    clipped = gpd.GeoSeries(voronoi).clip(polygon)

    # convert to networkx graph
    lines = clipped.explode(index_parts=False).reset_index(drop=True)
    lines = gpd.GeoDataFrame(geometry=lines)
    G = lines_to_graph(lines)
    subgraphs = nx.connected_components(G)
    largest = max(subgraphs, key=len)
    G = G.subgraph(largest)
    return G


def sinuosity(linestring):
    start = linestring.interpolate(0)
    end = linestring.interpolate(1, normalized=True)
    return linestring.length / start.distance(end)


def lines_to_graph(gdf):
    nodes = {}
    count = 0
    G = nx.Graph()
    for i, linestring in enumerate(gdf.geometry):
        c1 = linestring.coords[0]
        c2 = linestring.coords[-1]
        if c1 not in nodes:
            nodes[c1] = count
            count += 1
        if c2 not in nodes:
            nodes[c2] = count
            count += 1
        G.add_node(nodes[c1], linestring=i, coords=c1)
        G.add_node(nodes[c2], linestring=i, coords=c2)
        G.add_edge(nodes[c1], nodes[c2], linestring=i)
    return G


def boundary_nodes(g):
    boundary_nodes = [i for i in g.nodes() if len(list(g.neighbors(i))) == 1]
    records = []
    for node in boundary_nodes:
        data = g.nodes[node]
        record = {}
        record["linestring_id"] = data["linestring"]
        record["node_id"] = node
        record["geometry"] = Point(data["coords"])
        records.append(record)
    bn = pd.DataFrame.from_records(records)
    bn = gpd.GeoDataFrame(bn, geometry="geometry")
    return bn


def find_best_path(g, sources, targets):
    combinations = list(itertools.product(sources["node_id"], targets["node_id"]))
    all_paths = []
    for c in combinations:
        paths = nx.all_simple_paths(g, source=c[0], target=c[1])
        for p in paths:
            path = LineString([Point(g.nodes[n]["coords"]) for n in p])
            all_paths.append(path)
    all_paths = gpd.GeoDataFrame(geometry=all_paths)

    all_paths["length"] = all_paths.length
    # sort by length
    all_paths = all_paths.sort_values(by="length", ascending=False)
    longest_n = all_paths.iloc[0:5]

    # get 'sinuousity' of each path (path.length / distance)
    sins = longest_n.geometry.apply(sinuosity)
    best = longest_n.loc[sins.idxmin()]
    return best.geometry
