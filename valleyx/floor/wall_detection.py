from loguru import logger
from shapelysmooth import chaikin_smooth
from shapelysmooth import taubin_smooth
import xarray as xr

from valleyx.floor.smooth import filter_nan_gaussian_conserving
from valleyx.tools.network_xsections import network_xsections
from valleyx.tools.network_xsections import observe_values
from valleyx.floor.flood_extent.preprocess_profile import preprocess_profiles
from valleyx.floor.flood_extent.convert_wp import finalize_wallpoints

from valleyx.floor.flood_extent.classify_profile_max_ascent import (
    classify_profiles_max_ascent,
    invert_dem,
)
from valleyx.terrain.flow_dir import flowdir_wbt

logger.bind(module="wall_detection")


def detect_wallpoints(
    basin,
    ta,
    sigma,
    line_spacing,
    line_width,
    line_max_width,
    point_spacing,
    min_hand_jump,
    ratio,
    min_peak_prominence,
    min_distance,
    num_cells,
    slope_threshold,
    wbt,
):
    logger.info("Starting wall point detection")

    smoothed_data = filter_nan_gaussian_conserving(basin.dem.data, sigma)
    smoothed = basin.dem.copy()
    smoothed.data = smoothed_data

    slope, curvature = ta.elevation_derivatives(smoothed)

    logger.debug(f"Flowlines count: {len(basin.flowlines)}")
    logger.debug("Smoothing flowlines")
    flowlines = smooth_flowlines(basin.flowlines)

    logger.debug(
        f"Creating xsections, line interval: {line_spacing}, pt interval: {point_spacing}"
    )
    xsections = network_xsections(
        flowlines,
        line_spacing,
        line_width,
        point_spacing,
        line_max_width,
        basin.subbasins,
    )
    logger.debug(
        f"Number of xsections: {len(xsections['xsID'].unique())}, number of points: {len(xsections)}"
    )

    dataset = xr.Dataset()
    dataset["subbasin"] = basin.subbasins
    dataset["hillslope"] = basin.hillslopes
    dataset["hand"] = basin.hand
    dataset["slope"] = slope
    dataset["curvature"] = curvature
    dataset["flow_path"] = basin.flow_paths
    dataset["conditioned_dem"] = basin.conditioned_dem
    logger.debug(f"Observing values at cross section points, {dataset.data_vars}")

    xsections = observe_values(xsections, dataset)

    logger.debug("Preprocessing profiles")
    xsections = preprocess_profiles(
        xsections, min_hand_jump, ratio, min_distance, min_peak_prominence
    )
    logger.debug(
        f"Number of xsections after preprocessing: {len(xsections['xsID'].unique())}, number of points {len(xsections)}"
    )

    logger.debug(
        f"Finding wall points, num_cells: {num_cells}, slope: {slope_threshold}"
    )
    xsections = classify_profiles_max_ascent(
        xsections,
        dataset["conditioned_dem"],
        dataset["slope"],
        num_cells,
        slope_threshold,
        wbt,
    )
    wallpoints = xsections.loc[xsections["wallpoint"], "geom"]

    logger.debug(f"Number of wall points: {len(wallpoints)}")
    if len(wallpoints):  # atleast one wallpoints
        logger.debug("Finding upslope neighbor for each wall point")
        wallpoints = finalize_wp(wallpoints, dataset["conditioned_dem"], wbt, dataset)

    logger.success("Completed wall point detection")
    return wallpoints


def smooth_flowlines(flowlines, flowline_smooth_tolerance=3):
    smoothed = flowlines.apply(lambda x: x.simplify(flowline_smooth_tolerance))
    smoothed = smoothed.apply(lambda x: chaikin_smooth(taubin_smooth(x)))
    return smoothed


def finalize_wp(wallpoints, dem, wbt, dataset):
    inverted_dem = invert_dem(dem)
    fdir = flowdir_wbt(inverted_dem, wbt)
    wp = finalize_wallpoints(wallpoints, fdir)
    wp = observe_values(
        wp, dataset[["hand", "slope", "subbasin", "hillslope", "flow_path"]]
    )
    wp["streamID"] = wp["subbasin"]
    return wp
