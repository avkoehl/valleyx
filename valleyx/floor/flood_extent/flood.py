from loguru import logger

import xarray as xr
import pandas as pd
import geopandas as gpd
import numpy as np
from shapelysmooth import chaikin_smooth, taubin_smooth

from valleyx.floor.flood_extent.classify_profile_max_ascent import (
    classify_profiles_max_ascent,
    DIRMAPS,
)
from valleyx.floor.flood_extent.preprocess_profile import preprocess_profiles
from valleyx.tools.network_xsections import observe_values
from valleyx.tools.network_xsections import network_xsections
from valleyx.utils.raster import finite_unique, pixel_to_point, point_to_pixel


def flood(
    basin,
    slope,
    curvature,
    max_ascent_fdir,
    xs_spacing,
    xs_max_width,
    point_spacing,
    min_hand_jump,
    ratio,
    min_peak_prominence,
    min_distance,
    path_length,
    slope_threshold,
    min_points,
    percentile,
    buffer,
    default_threshold,
    spatial_radius,
    sigma,
):
    # create cross section profiles
    logger.debug("Creating cross section profiles")
    dataset = prep_data(basin, slope, curvature)
    xsections = network_xsections(
        smooth_flowlines(basin.flowlines),
        xs_spacing,
        xs_max_width,
        point_spacing,
        basin.subbasins,
    )
    xsections = observe_values(xsections, dataset)

    # preprocess cross section profiles
    logger.debug("Preprocessing cross section profiles")
    profiles = preprocess_profiles(
        xsections,
        min_hand_jump,
        ratio,
        min_distance,
        min_peak_prominence,
    )

    # detect boundary points
    logger.debug("Detecting boundary points")
    # convert path length to number of cells based on slope.rio.resolution
    num_cells = int(path_length / slope.rio.resolution()[0])
    xsections = classify_profiles_max_ascent(
        profiles,
        dataset["slope"],
        max_ascent_fdir,
        num_cells,
        slope_threshold,
    )
    boundary_pts = xsections.loc[xsections["wallpoint"], "geom"]
    if boundary_pts.empty:
        boundary_pts = None
    else:
        boundary_pts = post_process_pts(boundary_pts, dataset, max_ascent_fdir)

    logger.debug("Determining flood extents from boundary points")
    thresholds = determine_flood_extents(
        boundary_pts,
        dataset["subbasin"],
        dataset["hillslope"],
        min_points,
        percentile,
        buffer,
    )
    if default_threshold is not None:
        thresholds = thresholds.fillna(default_threshold)

    # apply flood thresholds
    logger.debug("Applying flood thresholds")
    flooded = apply_flood_thresholds(basin, thresholds)

    # add flowpath
    flowpaths = basin.flow_paths > 0
    flooded = flooded + flowpaths
    flooded = flooded > 0
    return flooded, thresholds, boundary_pts


def apply_flood_thresholds(basin, thresholds):
    flooded = basin.hand.copy()
    flooded.data = np.zeros_like(flooded.data)

    for _, row in thresholds.iterrows():
        if not np.isfinite(row["threshold"]):
            continue

        sub_condition = basin.subbasins == row["streamID"]
        hs_condition = basin.hillslopes == row["hillslopeID"]
        condition = sub_condition & hs_condition
        mask = basin.hand.where(condition)
        mask = (mask <= row["threshold"]).astype(int)
        flooded.data = np.maximum(flooded.data, mask.data)
    return flooded


def determine_flood_extents(
    boundary_pts,
    subbasins,
    hillslopes,
    min_points,
    percentile,
    buffer,
):
    results = []
    for reachID in finite_unique(subbasins):
        clipped_hillslopes = hillslopes.where(subbasins == reachID)
        for hillslopeID in finite_unique(clipped_hillslopes):
            result = {
                "streamID": reachID,
                "hillslopeID": hillslopeID,
                "threshold": None,
            }
            if hillslopeID == 0:
                continue

            if boundary_pts is None:
                results.append(result)
                continue

            points = boundary_pts.loc[boundary_pts["streamID"] == reachID]
            points = points.loc[points["hillslope"] == hillslopeID]

            if len(points) < min_points:
                results.append(result)
            else:
                threshold = np.quantile(points["hand"], percentile)
                threshold = threshold + buffer
                result["threshold"] = threshold
                results.append(result)
    return pd.DataFrame(results)


def prep_data(basin, slope, curvature):
    dataset = xr.Dataset()
    dataset["slope"] = slope
    dataset["curvature"] = curvature
    dataset["conditioned_dem"] = basin.conditioned_dem
    dataset["subbasin"] = basin.subbasins
    dataset["hillslope"] = basin.hillslopes
    dataset["hand"] = basin.hand
    dataset["flow_path"] = basin.flow_paths
    return dataset


def smooth_flowlines(flowlines, flowline_smooth_tolerance=3):
    smoothed = flowlines.apply(lambda x: x.simplify(flowline_smooth_tolerance))
    smoothed = smoothed.apply(lambda x: chaikin_smooth(taubin_smooth(x)))
    return smoothed


def post_process_pts(boundary_pts, dataset, fdir, dirmap=DIRMAPS["wbt"]):
    indices = [point_to_pixel(fdir, point) for point in boundary_pts]

    results = []
    for row, col in indices:
        direction = fdir[row, col].item()
        new_row = row + dirmap[direction][0]
        new_col = col + dirmap[direction][1]
        point = pixel_to_point(fdir, new_row, new_col)
        results.append({"geometry": point, "row": new_row, "col": new_col})

    df = pd.DataFrame.from_records(results)
    df = gpd.GeoDataFrame(df, geometry="geometry", crs=fdir.rio.crs)

    df = observe_values(
        df, dataset[["hand", "slope", "subbasin", "hillslope", "flow_path"]]
    )
    df["streamID"] = df["subbasin"]
    return df
