"""Core workflow for valley floor extraction."""

import geopandas as gpd
from loguru import logger
from typing import Optional
import whitebox
import xarray as xr
import time

from valleyx.config import ValleyConfig
from valleyx.flow.flow import flow_analysis
from valleyx.reach.reach import delineate_reaches
from valleyx.floor.floor import label_floors
from valleyx.terrain_analyzer import TerrainAnalyzer


def format_time_duration(seconds):
    """
    Format seconds into a human-readable time string.
    For longer durations, shows hours and minutes; for shorter ones, shows minutes and seconds.
    """

    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds:.2f}s"


def extract_valleys(
    dem: xr.DataArray,
    flowlines: gpd.GeoSeries,
    wbt: whitebox.WhiteboxTools,
    config: ValleyConfig,
    prefix: Optional[str] = None,
) -> xr.DataArray:
    """
    Extract valley floors complete workflow
    Parameters
    ----------
    dem : xarray.DataArray
        Digital elevation model
    flowlines : geopandas.GeoSeries
        Stream network as GeoSeries of LineString geometries
    wbt : WhiteboxTools
        Initialized WhiteboxTools instance
    config : dict
        Configuration parameters
    prefix : str, optional
        Prefix for temporary files
    Returns
    -------
    Tuple[xr.DataArray, gpd.GeoSeries]
    xr.DataArray
        Raster with valley floors labeled
    gpd.GeoSeries
        Stream network
    """
    start_time = time.time()
    logger.info("Starting valley extraction workflow")

    # Initialize terrain analyzer
    ta = TerrainAnalyzer(wbt, prefix)

    # Run analysis stages
    logger.info("Running flow analysis")
    flow_start_time = time.time()
    basin = flow_analysis(dem, flowlines, ta)
    flow_end_time = time.time()
    flow_duration = flow_end_time - flow_start_time

    logger.info("Delineating reaches")
    reach_start_time = time.time()
    basin = delineate_reaches(
        basin, ta, config.hand_threshold, config.spacing, config.minsize, config.window
    )
    reach_end_time = time.time()
    reach_duration = reach_end_time - reach_start_time

    logger.info("Detecting valley floors")
    floor_start_time = time.time()
    floor = label_floors(
        basin,
        ta,
        config.max_floor_slope,
        config.foundation_slope,
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
        config.buffer,
        config.min_points,
        config.percentile,
        config.default_threshold,
    )
    floor_end_time = time.time()
    floor_duration = floor_end_time - floor_start_time

    end_time = time.time()
    total_duration = end_time - start_time

    # Log timing information in a human-readable format
    logger.info(f"Flow analysis time: {format_time_duration(flow_duration)}")
    logger.info(f"Reach delineation time: {format_time_duration(reach_duration)}")
    logger.info(f"Floor detection time: {format_time_duration(floor_duration)}")
    logger.info(f"Total execution time: {format_time_duration(total_duration)}")

    logger.success("Valley extraction workflow completed")
    return floor, basin.flowlines
