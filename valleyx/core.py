# valleyx/core.py
"""Core workflow for valley floor extraction."""

import geopandas as gpd
import numpy as np
from loguru import logger
from typing import Optional
import whitebox
import xarray as xr

from valleyx.config import ValleyConfig
from valleyx.flow.flow import flow_analysis
from valleyx.reach.reach import delineate_reaches
from valleyx.floor.floor import label_floors
from valleyx.terrain_analyzer import TerrainAnalyzer


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
    xr.DataArray
        Raster with valley floors labeled
    """
    logger.info("Starting valley extraction workflow")

    # Initialize terrain analyzer
    ta = TerrainAnalyzer(wbt, prefix)

    # Run analysis stages
    logger.info("Running flow analysis")
    basin = flow_analysis(dem, flowlines, ta)

    logger.info("Delineating reaches")
    basin = delineate_reaches(
        basin, ta, config.hand_threshold, config.spacing, config.minsize, config.window
    )

    logger.info("Detecting valley floors")
    basin = label_floors(
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

    logger.success("Valley extraction workflow completed")
    return basin
