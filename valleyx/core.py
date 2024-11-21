from dataclasses import dataclass
from loguru import logger
from typing import Optional

from valleyx.flow_analysis import flow_analysis
from valleyx.reach_delineation import delineate_reaches
from valleyx.wall_detection import detect_wallpoints
from valleyx.label_floors import label_floors

logger.bind(module="core")

@dataclass
class ValleyConfig:

    # Reach delineation params
    hand_threshold: float
    spacing: int
    minsize: int
    window: int

    # Dem smoothing
    sigma: float

    # Cross Section Params
    line_spacing: int
    line_width: int
    line_max_width: int
    point_spacing: int

    # Cross section preprocessing
    min_hand_jump: int
    ratio: float
    min_peak_prominence: int
    min_distance: int

    # Sustained slope params
    num_cells: int
    slope_threshold: float

    # Floor labeling params
    foundation_slope: float
    buffer: float
    min_points: int
    percentile: float
    max_floor_slope: Optional[float] = None 

    @classmethod
    def from_dict(cls, config_dict: dict):
        return cls(**config_dict)


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
        config.line_max_width,,
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

    return {
            'floor': floor,
            'flowlines': flowlines,
            'wallpoints': wallpoints
            }
