from loguru import logger
import numpy as np
from scipy.ndimage import binary_closing
from skimage.morphology import remove_small_holes

from valleyx.floor.smooth import filter_nan_gaussian_conserving
from valleyx.floor.foundation.connect import connected
from valleyx.floor.flood_extent.flood import flood
from valleyx.floor.foundation.foundation import foundation
from valleyx.utils.flowpaths import find_first_order_reaches

logger.bind(module="label_floors")


def label_floors(
    basin,
    ta,
    max_floor_slope,
    max_fill_area,
    spatial_radius,
    foundation_threshold,
    sigma,
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
    fspatial_radius,
    fsigma,
):
    logger.info("Labeling floors")
    logger.debug("smoothing dem with sigma: {}", sigma)
    logger.debug("computing slope and curvature")
    smoothed_data = filter_nan_gaussian_conserving(
        basin.dem.data, spatial_radius, basin.dem.rio.resolution()[0], sigma
    )
    smoothed = basin.dem.copy()
    smoothed.data = smoothed_data
    slope_smooth = ta.slope(smoothed)

    logger.debug("computing foundation floor")
    first_order_reaches = find_first_order_reaches(basin.flowlines)
    filtered_flow_paths = basin.flow_paths.copy()
    for reach in first_order_reaches:
        filtered_flow_paths.data[filtered_flow_paths.data == reach] = 0
    foundation_floor = foundation(
        slope_smooth, filtered_flow_paths, foundation_threshold
    )

    logger.debug("computing flood extents")
    smoothed_data_flood = filter_nan_gaussian_conserving(
        basin.dem.data, fspatial_radius, basin.dem.rio.resolution()[0], fsigma
    )
    smoothed_flood = basin.dem.copy()
    smoothed_flood.data = smoothed_data_flood
    slope = ta.slope(smoothed_flood)
    curvature = ta.curvature(smoothed_flood)
    inverted_dem = -1 * (basin.dem - basin.dem.max().item()) + basin.dem.min().item()
    max_ascent_fdir = ta.flow_pointer(inverted_dem)
    flood_extent_floor, hand_thresholds, boundary_points = flood(
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
        fspatial_radius,
        fsigma,
    )

    combined = foundation_floor + flood_extent_floor
    combined = combined > 0
    combined = combined.astype(np.uint8)

    # remove high slope
    if max_floor_slope is not None:
        combined.data[slope.data > max_floor_slope] = 0

    # fill holes
    combined.data = binary_closing(combined.data, structure=np.ones((3, 3)))

    # burnin flowpaths
    combined.data[basin.flow_paths.data > 0] = 1

    # keep only regions that are connected to the flowpath network
    combined = connected(combined, basin.flow_paths)

    # remove small regions
    # convert area to number of cells based on basin.rio.resolution
    if max_fill_area:
        num_cells = max_fill_area / (basin.dem.rio.resolution()[0] ** 2)
        num_cells = int(num_cells)
        combined.data = remove_small_holes(combined.data, num_cells)

    combined = combined.astype(np.uint8)
    flood_extent_floor = flood_extent_floor.astype(np.uint8)
    foundation_floor = foundation_floor.astype(np.uint8)
    return (
        flood_extent_floor,
        foundation_floor,
        combined,
        hand_thresholds,
        boundary_points,
    )
