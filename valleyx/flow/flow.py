from loguru import logger

from valleyx.basin import BasinData
from valleyx.flow.flowpaths import (
    find_channel_heads,
    prep_flowlines,
    pour_points_from_flowpaths,
)
from valleyx.utils.raster import finite_unique

logger.bind(module="flow_analysis")


def flow_analysis(dem, flowlines, ta):
    """
    Align flowlines to flow accumulation paths
    delineate subbasins and hillslopes
    compute hand

    Parameters
    ----------
    dem : xarray.DataArray
        Digital Elevation Model raster
    flowlines : geopandas.GeoSeries or GeoDataFrame
        Vector stream network to be aligned with flow accumulation
    ta : TerrainAnalyzer

    Returns
    -------
    BasinData
    """

    logger.info("Starting flowline processing")

    logger.info("Running flow accumulation workflow")
    conditioned, flow_dir, flow_acc = ta.flow_acc_workflow(dem)

    logger.info("Extracting flowpaths")
    channel_heads = find_channel_heads(flowlines)
    flowlines, flow_path = ta.trace_flowpaths(
        flow_dir, flow_acc, channel_heads, snap_dist=50
    )
    flowlines = prep_flowlines(flowlines, flow_acc)

    logger.info("computing subbasins and hillslopes")
    pour_points = pour_points_from_flowpaths(flow_path, flow_acc)
    subbasin = ta.subbasins(flow_dir, pour_points)
    hillslope = ta.hillslopes(flow_dir, flow_path)

    logger.info("Computing channel relief (HAND)")
    hand = ta.hand(conditioned, flow_path)

    basin_data = BasinData(
        dem=dem,
        flowlines=flowlines,
        conditioned_dem=conditioned,
        flow_dir=flow_dir,
        flow_acc=flow_acc,
        flow_paths=flow_path,
        subbasins=subbasin,
        hillslopes=hillslope,
        hand=hand,
    )
    logger.debug(f"Number of flowlines: {len(flowlines)}")
    logger.debug(f"Number of subbasins: {len(finite_unique(subbasin))}")
    logger.success("Flowline processing completed succesfully")
    return basin_data
