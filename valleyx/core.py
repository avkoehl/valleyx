"""Core workflow for valley floor extraction."""

import os
import shutil

import geopandas as gpd
from loguru import logger
from typing import Optional
import whitebox
import xarray as xr
import time
from typing import Dict, Tuple, Optional, Union

from valleyx.config import ValleyConfig
from valleyx.flow.flow import flow_analysis
from valleyx.reach.reach import delineate_reaches
from valleyx.floor.floor import label_floors
from valleyx.terrain_analyzer import TerrainAnalyzer


def setup_wbt(working_dir, verbose, max_procs):
    wbt = whitebox.WhiteboxTools()

    working_dir = os.path.abspath(os.path.expanduser(working_dir))
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)
    wbt.set_working_dir(working_dir)

    wbt.set_verbose_mode(verbose)  # default True
    wbt.set_max_procs(max_procs)  # default -1
    return wbt


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
    config: ValleyConfig,
    wbt: Optional[whitebox.WhiteboxTools] = None,
    prefix: Optional[str] = None,
    debug_returns: bool = False,
) -> Union[
    Tuple[xr.DataArray, gpd.GeoSeries], Tuple[Tuple[xr.DataArray, gpd.GeoSeries], Dict]
]:
    """
        Extract valley floors from a digital elevation model and flowlines.

    Parameters
    ----------
    dem : xarray.DataArray
        Digital elevation model as a raster
    flowlines : geopandas.GeoSeries
        Stream network as GeoSeries of LineString geometries
    config : ValleyConfig
        Configuration parameters for the valley extraction workflow.
        See help(ValleyConfig) for details on available parameters.
    wbt : WhiteboxTools, optional
        Initialized WhiteboxTools instance. If None, a new instance will be created
        with default parameters.
    prefix : str, optional
        Prefix for temporary files. Useful when running multiple extractions
        in parallel.
    debug_returns : bool, default=False
        If True, returns additional debug information including hand thresholds
        and boundary points.

    Returns
    -------
    Union[Tuple[xr.DataArray, gpd.GeoSeries], Tuple[Tuple[xr.DataArray, gpd.GeoSeries], Dict]]
        When debug_returns=False:
            A tuple containing (floors, flowlines) where:
            - floors: xr.DataArray - Binary raster with valley floors labeled
            - flowlines: gpd.GeoSeries - Stream network used for the analysis

        When debug_returns=True:
            A tuple containing ((floors, flowlines), debug_info) where:
            - (floors, flowlines): Same as above
            - debug_info: Dict containing additional data:
                - 'labeled_floors': Valley floors labeled with subbasin IDs
                - 'hand_thresholds': HAND threshold values for each reach
                - 'boundary_points': Boundary points used for valley delineation

    """

    start_time = time.time()
    logger.info("Starting valley extraction workflow")

    # Check if WhiteboxTools is available
    if wbt is None:
        working_dir = os.path.join(os.getcwd(), "whitebox_temp")
        verbose = False
        max_procs = -1
        wbt = setup_wbt(working_dir, verbose, max_procs)

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
        basin,
        ta,
        config.reach.hand_threshold,
        config.reach.spacing,
        config.reach.minsize,
        config.reach.window,
    )
    reach_end_time = time.time()
    reach_duration = reach_end_time - reach_start_time

    logger.info("Detecting valley floors")
    floor_start_time = time.time()
    floor, hand_thresholds, boundary_points = label_floors(
        basin,
        ta,
        config.floor.max_floor_slope,
        config.floor.max_fill_area,
        config.floor.foundation.slope,
        config.floor.foundation.sigma,
        config.floor.flood.xs_spacing,
        config.floor.flood.xs_max_width,
        config.floor.flood.point_spacing,
        config.floor.flood.min_hand_jump,
        config.floor.flood.ratio,
        config.floor.flood.min_peak_prominence,
        config.floor.flood.min_distance,
        config.floor.flood.path_length,
        config.floor.flood.slope_threshold,
        config.floor.flood.min_points,
        config.floor.flood.percentile,
        config.floor.flood.buffer,
        config.floor.flood.default_threshold,
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

    # cleanup
    if os.path.exists(wbt.work_dir):
        shutil.rmtree(wbt.work_dir)

    logger.success("Valley extraction workflow completed")

    # Always return these core elements
    required_results = (floor, basin.flowlines)

    # Optionally return debug info
    if debug_returns:
        debug_info = {
            "labeled_floors": basin.subbasins * floor,
            "hand_thresholds": hand_thresholds,
            "boundary_points": boundary_points,
        }
        return required_results, debug_info

    return required_results
