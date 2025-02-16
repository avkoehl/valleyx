"""
input:
    flowpaths
    flowdir
    subbasins
output:
    hillslopes
"""

import os

import rioxarray as rxr
import numpy as np
import xarray as xr

from valleyx.raster.raster_utils import finite_unique
from valleyx.utils import WhiteBoxToolsUnique


def label_hillslopes(
    flow_paths: xr.DataArray,
    flow_dir: xr.DataArray,
    subbasins: xr.DataArray,
    wbt: WhiteboxToolsUnique,
) -> xr.DataArray:
    """
    Label the catchment areas draining into the flowpaths. This includes the
    left side, right side, and all the areas that flow into the channel head
    point.

    It will find and label the catchment for each unique flowpath,
    so if the flowpaths have been segmented into reaches it will still work.

    Parameters
    ----------
    flow_paths: xr.DataArray
        A raster representing the stream_network, each stream cell is labeled
        by stream_id, non stream cells are 0 or NoData
    flow_dir: xr.DataArray
        A raster representing the flow direction in whitebox pointer format
    subbasins: xr.DataArray
        A raster with each subbasin labeled, must match flow_paths
    wbt: WhiteboxTools
        An instance of the WhiteboxTools class

    Returns
    -------
    hillslopes: xr.DataArray
    """
    assert set(finite_unique(subbasins).astype(np.float32)) == set(
        finite_unique(flow_paths).astype(np.float32)
    )

    hillslopes = flow_paths.copy()
    hillslopes.data = np.zeros_like(flow_paths)

    for streamID in finite_unique(subbasins):
        basin_mask = subbasins == streamID
        flowpath_clipped = flow_paths.where(basin_mask)
        flowdir_clipped = flow_dir.where(basin_mask)
        basins = wbt_label_drainage_sides(flowdir_clipped, flowpath_clipped, wbt)
        mask = ~np.isnan(basins)
        hillslopes = hillslopes.where(~mask, other=basins)
    return hillslopes


def wbt_label_drainage_sides(
    flow_dir: xr.DataArray, flow_paths: xr.DataArray, wbt: WhiteBoxToolsUnique
) -> xr.DataArray:
    """
    Wrapper around whiteboxtools Hillslopes tool.

    Parameters
    ----------
    flow_dir: xr.DataArray
        A raster representing the flow direction in whitebox pointer format
    flow_paths: xr.DataArray
        A raster representing the stream_network, each stream cell is labeled
        by stream_id, non stream cells are 0 or NoData
    wbt: WhiteBoxTools
        An instance of the WhiteboxTools class

    Returns
    -------
    hillslopes: xr.DataArray
        A raster with each catchment side labeled.
    """
    files = {
        "temp_flowdir": os.path.join(
            wbt.work_dir, f"{wbt.instance_id}-temp_flowdir.tif"
        ),
        "temp_flowpaths": os.path.join(
            wbt.work_dir, f"{wbt.instance_id}-temp_flowpaths.tif"
        ),
        "hillslopes": os.path.join(wbt.work_dir, f"{wbt.instance_id}-hillslopes.tif"),
    }
    flow_dir.rio.to_raster(files["temp_flowdir"])
    flow_paths.rio.to_raster(files["temp_flowpaths"])

    wbt.hillslopes(files["temp_flowdir"], files["temp_flowpaths"], files["hillslopes"])

    with rxr.open_rasterio(files["hillslopes"], masked=True) as raster:
        hillslopes = raster.squeeze().copy()

    os.remove(files["temp_flowdir"])
    os.remove(files["temp_flowpaths"])
    return hillslopes
