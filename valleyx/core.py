from loguru import logger

from valleyx.flow_analysis import flow_analysis
from valleyx.reach_delineation import delineate_reaches
from valleyx.wall_detection import detect_wallpoints
from valleyx.label_floors import label_floors

logger.bind(module="core")


def extract_valleys(dem, flowlines, wbt, config):
    logger.info("Running extract valleys workflow")
    flowlines, dataset = flow_analysis(dem, flowlines, wbt)
    flowlines, dataset = delineate_reaches(
        dataset,
        flowlines,
        wbt,
        config.hand_threshold,
        config.spacing,
        config.minsize,
        config.window,
    )
    wallpoints = detect_wallpoints(
        dataset,
        flowlines,
        config.sigma,
        config.line_spacing,
        config.line_width,
        config.line_max_width,
        config.point_spacing,
        config.min_hand_jump,
        config.ratio,
        config.min_peak_prominence,
        config.min_distance,
        config.num_cells,
        config.slope_threshold,
        wbt,
    )
    floor = label_floors(
        wallpoints,
        dataset,
        config.max_floor_slope,
        config.foundation_slope,
        config.buffer,
        config.min_points,
        config.percentile,
    )
    logger.success("Finished extract valleys workflow")

    return {"floor": floor, "flowlines": flowlines, "wallpoints": wallpoints}
