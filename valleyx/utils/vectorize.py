import warnings

import geopandas as gpd
import numpy as np
from rasterio import features
from shapely.geometry import shape

from valleyx.utils.raster import finite_unique
from valleyx.utils.geometry import tidy_polygons


def polygonize_feature(raster, feature_value=1):
    # get polygons that correspond to the regions where raster == feature_value
    # wrapper for rasterio.features.shapes
    # raster is a numeric array and feature_value is the value of the feature to polygonize

    # create a mask where the raster is equal to the feature value
    # this will be used to mask the raster when calling rasterio.features.shapes
    # because we only want to have to operate on the pixels that are equal to the feature value
    mask = raster == feature_value

    polygons = []
    for geom, value in features.shapes(
        raster, mask=mask, transform=raster.rio.transform()
    ):
        if value == feature_value:  #
            # load the geometry as a shapely Polygon and append to the list
            polygons.append(shape(geom))
    return polygons


def shapes_from_int_raster(raster):
    # wrapper around rasterio.features_module that returns a geodataframe
    # raster should be relatively simple.
    # values of 0 are considered nodata
    if not any(
        raster.dtype == t
        for t in [np.int8, np.int16, np.int32, np.uint8, np.uint16, np.uint32]
    ):
        raise ValueError("Array dtype is not int")

    results = features.shapes(raster, transform=raster.rio.transform())
    records = []
    for polygon, value in results:
        poly = shape(polygon)
        record = {"geometry": poly, "feature_value": value}
        records.append(record)

    df = gpd.GeoDataFrame.from_records(records)
    df = gpd.GeoDataFrame(df, geometry="geometry", crs=raster.rio.crs)
    df = df.sort_values(by="feature_value", ascending=True, inplace=False)
    df = df.loc[df["feature_value"] != 0]
    df = df.reset_index(drop=True)
    return df


def shapes_from_binary_raster(raster):
    # return polygons where raster == 1

    unique_values = finite_unique(raster)

    if not np.all((raster.data == 0) | (raster.data == 1)):
        raise ValueError("Array contains values other than 0 and 1")

    raster = raster.astype(np.uint8)

    polygons = []
    shapes_gen = features.shapes(raster.data, transform=raster.rio.transform())
    for poly, value in shapes_gen:
        if value:
            polygons.append(shape(poly))
    polygons = gpd.GeoSeries(polygons, crs=raster.rio.crs)

    return gpd.GeoSeries(polygons, crs=raster.rio.crs)


def single_polygon_from_binary_raster(binary_raster, min_percent_area=99):
    polygons = shapes_from_binary_raster(binary_raster)
    polygons = tidy_polygons(polygons)

    if len(polygons) > 1:
        percent_area = polygons.area / polygons.area.sum() * 100
        polygons = polygons.loc[percent_area > min_percent_area]

        if len(polygons) == 1:
            warnings.warn(
                f"Multiple polygons found. Returned polygon with area > {min_percent_area}% of total area"
            )
            return polygons.iloc[0]
        else:
            raise ValueError("attempt to find single polygon failed")

    if len(polygons) == 0:
        return None
    else:
        return polygons.iloc[0]
