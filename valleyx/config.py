from dataclasses import dataclass
from typing import Optional


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
    default_threshold: Optional[float] = None

    @classmethod
    def from_dict(cls, config_dict: dict):
        return cls(**config_dict)
