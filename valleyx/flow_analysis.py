from loguru import logger
import xarray as xr

from valleyx.terrain.flow_acc import flow_accumulation_workflow
from valleyx.terrain.align_flowlines import align_flowlines
from valleyx.terrain.subbasins import label_subbasins
from valleyx.terrain.hillslopes import wbt_label_drainage_sides
from valleyx.terrain.hand import channel_relief
from valleyx.raster.raster_utils import finite_unique

logger.bind(module="flow_analysis")


def flow_analysis(dem, flowlines, wbt):
    """
    Perform comprehensive flow analysis on a DEM using provided flowlines.

    This function executes a hydrological analysis workflow:
    1. DEM conditioning and flow routing
    2. Flowline alignment with flow accumulation
    3. Subbasin delineation
    4. Height Above Nearest Drainage (HAND) calculation

    Parameters
    ----------
    dem : xarray.DataArray
        Digital Elevation Model raster
    flowlines : geopandas.GeoSeries or GeoDataFrame
        Vector stream network to be aligned with flow accumulation
    wbt : WhiteboxTools
        Initialized WhiteboxTools object for running hydrological analyses

    Returns
    -------
    tuple
        A tuple containing:
        - aligned_flowlines (geopandas.GeoSeries):
            Stream network aligned with flow accumulation paths
        - dataset (xarray.Dataset):
            Multi-layer dataset containing:
            * conditioned_dem: Hydrologically corrected DEM
            * flow_dir: D8 flow direction grid
            * flow_acc: Flow accumulation grid
            * flow_path: Rasterized stream network
            * subbasin: Labeled subbasin grid
            * hand: Height Above Nearest Drainage

    Examples
    --------
    >>> import whitebox
    >>> wbt = whitebox.WhiteboxTools()
    >>> aligned_flows, hydro_layers = flow_analysis(dem_array, stream_network, wbt)
    >>> hand_raster = hydro_layers['hand']
    """

    logger.info("Starting flowline processing")
    conditioned, flow_dir, flow_acc = flow_accumulation_workflow(dem, wbt)
    aligned_flowlines, flow_path = align_flowlines(flowlines, flow_acc, flow_dir, wbt)
    subbasin = label_subbasins(flow_dir, flow_acc, flow_path, wbt)
    hillslope = wbt_label_drainage_sides(flow_dir, flow_path, wbt)
    hand = channel_relief(conditioned, flow_path, wbt, method="d8")

    dataset = xr.Dataset()
    dataset["conditioned_dem"] = conditioned
    dataset["flow_dir"] = flow_dir
    dataset["flow_acc"] = flow_acc
    dataset["flow_path"] = flow_path
    dataset["subbasin"] = subbasin
    dataset["hillslope"] = hillslope
    dataset["hand"] = hand

    logger.debug(f"Number of flowlines: {len(flowlines)}")
    logger.debug(f"Number of flowlines after alignment: {len(aligned_flowlines)}")
    logger.debug(f"Number of subbasins: {len(finite_unique(dataset['subbasin']))}")
    logger.success("Flowline processing completed succesfully")
    return aligned_flowlines, dataset
