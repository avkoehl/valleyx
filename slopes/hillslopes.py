"""
input:
    flowpaths
    flowdir
    subbasins
output:
    hillslopes
"""
import rioxarray as rxr
import numpy as np
import xarray as xr
import skimage
from valleyfloor.flow.hillslope import label_drainage_sides

from .utils import finite_unique

def label_hillslopes(flow_paths: xr.DataArray, flow_dir: xr.DataArray, flow_acc:
                     xr.DataArray, subbasins: xr.DataArray) -> xr.DataArray:
    """
    Label the catchment areas draining into the flowpaths. This includes the
    left side, right side, and all the areas that flow into the channel head
    point.  

    Parameters
    ----------
    flow_paths: xr.DataArray
        A raster representing the stream_network, each stream cell is labeled
        by stream_id, non stream cells are 0 or NoData
    flow_dir: xr.DataArray
        A raster representing the flow direction in whitebox pointer format
    flow_acc: xr.DataArray
        A raster representing the flow accumulation for each cell
    subbasins: xr.DataArray
        A raster with each subbasin labeled, must match flow_paths

    Returns
    -------
    hillslopes: xr.DataArray
    """
    assert(set(finite_unique(subbasins)) == set(finite_unique(flow_paths)))

    hillslopes = flow_paths.copy()
    hillslopes.data = np.zeros_like(flow_paths)

    for streamID in finite_unique(subbasins):
        print(streamID)
        basin_mask = (subbasins == streamID)
        flowpath_clipped = flow_paths.where(basin_mask)
        flowacc_clipped = flow_acc.where(basin_mask)
        flowdir_clipped = flow_dir.where(basin_mask)
        basins = label_drainage_sides(flowpath_clipped, flowdir_clipped,
                                      flowacc_clipped)
        mask = ~np.isnan(basins)
        hillslopes = hillslopes.where(~mask, other=basins)
    return hillslopes 

