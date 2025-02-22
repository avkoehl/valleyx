from loguru import logger
import numpy as np
from scipy.ndimage import binary_closing

from valleyx.floor.smooth import filter_nan_gaussian_conserving
from valleyx.floor.foundation.connect import connected
from valleyx.floor.flood_extent.flood import flood
from valleyx.floor.foundation.foundation import foundation

logger.bind(module="label_floors")


def label_floors(
    basin,
    ta,
    max_floor_slope,
    foundation_threshold,
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
    buffer,
    min_points,
    percentile,
    default_threshold,
):
    logger.info("Labeling floors")
    logger.debug("smoothing dem with sigma: {}", sigma)
    logger.debug("computing slope and curvature")
    smoothed_data = filter_nan_gaussian_conserving(basin.dem.data, sigma)
    smoothed = basin.dem.copy()
    smoothed.data = smoothed_data
    slope, curvature = ta.elevation_derivatives(smoothed)

    logger.debug("computing foundation floor")
    foundation_floor = foundation(slope, basin.flow_paths, foundation_threshold)

    logger.debug("computing flood extents")
    inverted_dem = -1 * (basin.dem - basin.dem.max().item()) + basin.dem.min().item()
    max_ascent_fdir = ta.flow_pointer(inverted_dem)
    flood_extent_floor = flood(
        basin,
        slope,
        curvature,
        max_ascent_fdir,
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
        min_points,
        percentile,
        buffer,
        default_threshold,
    )

    combined = foundation_floor + flood_extent_floor
    combined = combined > 0
    combined = combined.astype(np.uint8)

    # remove high slope
    combined.data[slope.data > max_floor_slope] = 0

    # fill holes
    combined.data = binary_closing(combined.data, structure=np.ones((3, 3)))

    # keep only regions that are connected to the flowpath network
    combined = connected(combined, basin.flow_paths)
    return combined
