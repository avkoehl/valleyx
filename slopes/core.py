from dataclasses import dataclass
from loguru import logger

from slopes.flow_analysis import flow_analysis
from slopes.reach_delineation import delineate_reaches
from slopes.wall_detection import detect_wallpoints
from slopes.label_floors import label_floors
from slopes.label_floors import subbasin_floors

logger.bind(module="core")

@dataclass
class ValleyConfig:

    # Reach delineation params
    hand_threshold: float
    spacing: float
    minsize: int
    window: int

    # Dem smoothing
    sigma: float

    # Cross Section Params
    line_spacing: float
    line_width: float
    point_spacing: float

    # Cross section preprocessing
    min_hand_jump: float
    ratio: float
    min_peak_prominence: float
    min_distance: int

    # Sustained slope params
    num_cells: int
    slope_threshold: float

    # Floor labeling params
    hillslope_threshold: float
    plains_threshold: float
    buffer: float
    min_points: int
    percentile: float

    @classmethod
    def from_dict(cls, config_dict: dict):
        return cls(**config_dict)


def extract_valleys(dem, flowlines, wbt, config, return_flowlines=True):
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
        config.hillslope_threshold,
        config.plains_threshold,
        config.buffer,
        config.min_points,
        config.percentile,
    )
    floor = subbasin_floors(floor, dataset["subbasin"])
    logger.success("Finished extract valleys workflow")

    if return_flowlines:
        return floor, flowlines
    else:
        return floor
