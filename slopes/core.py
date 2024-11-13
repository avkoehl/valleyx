from dataclasses import dataclass
from loguru import logger

from slopes.utils import setup_wbt
from slopes.flow_analysis import flow_analysis
from slopes.reach_delineation import delineate_reaches
from slopes.wall_detection import detect_wallpoints
from slopes.floor.floor import label_floors
from slopes.raster.raster_utils import finite_unique

logger.bind(module="core")

wbt = setup_wbt("wbt_working_dir")
dem = rxr.open_rasterio("./data/input/dem.tif", masked=True).squeeze()
flowlines = gpd.read_file("./data/input/flowlines.shp")

@dataclass
class ValleyConfig:
    # Flow analysis params
    hand_threshold: float
    spacing: float
    minsize: int
    window: int
    
    # Wall detection params
    sigma: float
    line_spacing: float
    line_width: float
    point_spacing: float
    min_hand_jump: float
    ratio: float
    min_peak_prominence: float
    min_distance: int
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

def extract_valleys(dem, flowlines, wbt, config, return_flowlines=True)
    logger.info("Running extract valleys workflow")
    flowlines, dataset = flow_analysis(dem, flowlines, wbt)
    flowlines, dataset = delineate_reaches(flowlines, dataset, wbt, hand_threshold, spacing, minsize, window)
    wallpoints = detect_wallpoints(dataset, flowlines, sigma, line_spacing, line_width, point_spacing, min_hand_jump, ratio, min_peak_prominence, min_distance, num_cells, slope_threshold, wbt)
    logger.debug("Labeling floors")
    floor = label_floors(wallpoints, dataset, hillslope_threshold, plains_threshold, buffer, min_points, percentile)
    floor = subbasin_floors(floor, dataset['subbasin'])
    logger.success("Finished extract valleys workflow")

    if return_flowlines:
        return floor, flowlines
    else:
        return floor

def subbasin_floors(floor, subbasins):
    result = floor.copy()
    floor_condition = (floor > 0)
    for subbasinID in finite_unique(subbasins):
        condition = (subbasins.data == subbasinID)
        result.data[floor_condition & condition] = subbasinID
    return result

