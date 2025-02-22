import geopandas as gpd
import shapely
import shapely.geometry
from shapely.geometry import Polygon, Point, LineString, MultiPoint
from shapely.ops import unary_union, nearest_points


def close_holes(poly):
    if len(poly.interiors):
        return Polygon(list(poly.exterior.coords))
    return poly


def get_length_and_width(polygon):
    box = polygon.minimum_rotated_rectangle
    x, y = box.exterior.coords.xy
    edge_lengths = (
        Point(x[0], y[0]).distance(Point(x[1], y[1])),
        Point(x[1], y[1]).distance(Point(x[2], y[2])),
    )
    return edge_lengths


def get_points_on_linestring(linestring, spacing):
    points = []
    for i in range(0, int(linestring.length), spacing):
        point = linestring.interpolate(i)
        points.append(point)
    points.append(Point(linestring.coords[-1]))
    return points


def tidy_polygons(polygons):
    if type(polygons) not in [list, gpd.GeoSeries, gpd.GeoDataFrame]:
        raise ValueError("polygons must be a list, GeoSeries or GeoDataFrame")

    if isinstance(polygons, list):
        polygons = gpd.GeoSeries(polygons)

    polygons = polygons.buffer(0.1)  # silly but effective
    combined = unary_union(polygons)
    if isinstance(combined, shapely.geometry.polygon.Polygon):
        return gpd.GeoSeries(combined)
    else:
        return polygons


def extend_linestring(linestring, point):
    # find if start or end of linestring is closer
    distances = gpd.GeoSeries(
        [Point(linestring.coords[0]), Point(linestring.coords[-1])]
    ).distance(point)
    # add point to the list of points either at start or end
    coord_list = linestring.coords[:]
    if distances.iloc[0] <= distances.iloc[1]:  # point closer to start
        coord_list.insert(0, point.coords[0])
    else:  # point closer to end
        coord_list.append(point.coords[0])

    # make a new linestring
    linestring = LineString(coord_list)
    return linestring


def create_points_along_boundary(polygon, num_points):
    boundary = polygon.boundary
    boundary_length = boundary.length
    interval_length = boundary_length / num_points
    points = []

    distance = 0
    while distance <= boundary_length:
        point = boundary.interpolate(distance)
        points.append(point)
        distance += interval_length

    points.append(points[0])  # close the loop of points back at start
    return points


def add_point_to_polygon_exterior(polygon, point):
    # experimental and may lead to unnatural polygons if the point is far from the boundaries
    exterior = polygon.exterior
    exterior_coords_mp = MultiPoint(exterior.coords)
    exterior_coords_list = list(exterior.coords)

    _, p2 = nearest_points(
        point, exterior_coords_mp
    )  # get nearest boundary point to Point
    index = exterior_coords_list.index((p2.x, p2.y))

    # insert point right after closest vertex
    exterior_coords_list.insert(index + 1, (point.x, point.y))

    new_polygon = Polygon(exterior_coords_list)
    return new_polygon
