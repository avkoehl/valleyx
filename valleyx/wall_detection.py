from loguru import logger
from shapelysmooth import chaikin_smooth
from shapelysmooth import taubin_smooth

from valleyx.terrain.surface import elev_derivatives
from valleyx.profile.network_xsections import network_xsections
from valleyx.profile.network_xsections import observe_values
from valleyx.profile.preprocess_profile import preprocess_profiles
from valleyx.profile.convert_wp import finalize_wallpoints
from valleyx.max_ascent.classify_profile_max_ascent import classify_profiles_max_ascent
from valleyx.max_ascent.max_ascent import invert_dem
from valleyx.terrain.flow_dir import flowdir_wbt

logger.bind(module="wall_detection")


def detect_wallpoints(
    dataset,
    flowlines,
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

    req = ["subbasin", "conditioned_dem", "flow_path", "hillslope", "hand"]
    missing = [col for col in req if col not in dataset.data_vars]
    if missing:
        raise ValueError(f"Missing required layers: {', '.join(missing)}")

    logger.debug("Computing elevation derivatives")
    dataset["smoothed"], dataset["slope"], dataset["curvature"] = elev_derivatives(
        dataset["conditioned_dem"], wbt, sigma
    )

    logger.debug(f"Flowlines count: {len(flowlines)}")
    logger.debug("Smoothing flowlines")
    flowlines = smooth_flowlines(flowlines)

    logger.debug(
        f"Creating xsections, line interval: {line_spacing}, pt interval: {point_spacing}"
    )
    xsections = network_xsections(
        flowlines, line_spacing, line_width, point_spacing, line_max_width, dataset["subbasin"]
    )
    logger.debug(
        f"Number of xsections: {len(xsections['xsID'].unique())}, number of points: {len(xsections)}"
    )
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
    if len(wallpoints): # atleast one wallpoints
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
