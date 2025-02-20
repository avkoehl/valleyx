"""
Assumes flowpaths are properly aligned

input:
    flowdir
    flowacc
    flowpaths
output:
    subbasins
"""

import os
import shutil

import geopandas as gpd
import numpy as np
import rioxarray as rxr
import xarray as xr

from valleyx.utils import make_dir
from valleyx.utils import translate_to_wbt
from valleyx.utils import WhiteBoxToolsUnique
from valleyx.raster.raster_utils import pixel_to_point
from valleyx.raster.raster_utils import finite_unique


def label_subbasins(
    flow_dir: xr.DataArray,
    flow_acc: xr.DataArray,
    flow_paths: xr.DataArray,
    wbt: WhiteBoxToolsUnique,
) -> xr.DataArray:
    """
    Labels subbasins for a given flow_path raster

    Parameters
    ----------
    flow_dir: xr.DataArray
        A raster representing the flow direction in whitebox pointer format
    flow_acc: xr.DataArray
        A raster representing the flow accumulation for each cell
    flow_paths: xr.DataArray
        A raster representing the stream_network, each stream cell is labeled
        by stream_id, non stream cells are 0 or NoData
    wbt: WhiteboxToolsUnique
        An instance of the WhiteboxTools class

    Returns
    -------
    subbasins: xr.DataArray
        A raster with each subbasin labeled according to which segment in the
        stream network that cell flows into. Labels follow the labels used
        by 'flow_paths' input
    """
    pour_points = _pour_points_from_flowpaths(flow_paths, flow_acc)

    work_dir = wbt.work_dir
    temp_dir = os.path.join(work_dir, f"{wbt.instance_id}_subbasin_temp")
    make_dir(temp_dir)
    files = {
        "temp_flowdir": os.path.join(temp_dir, f"{wbt.instance_id}-temp_flowdir.tif"),
        "temp_pour_points": os.path.join(
            temp_dir, f"{wbt.instance_id}-temp_pour_points.shp"
        ),
        "subbasins": os.path.join(work_dir, f"{wbt.instance_id}-subbasins.tif"),
    }
    flow_dir.rio.to_raster(files["temp_flowdir"])
    pour_points.to_file(files["temp_pour_points"])

    wbt.watershed(files["temp_flowdir"], files["temp_pour_points"], files["subbasins"])

    with rxr.open_rasterio(files["subbasins"], masked=True) as raster:
        subbasins = raster.squeeze().copy()

    shutil.rmtree(temp_dir)

    # need to relabel the sections of subbasin to match the flowpaths
    mapping = {}
    ind = 1  # subbasins starts at 1 from whiteboxtools
    for streamID in finite_unique(flow_paths):
        mapping[ind + 0.1] = streamID
        ind += 1
    subbasins = subbasins + 0.1

    for key, value in mapping.items():
        subbasins.data[subbasins == key] = value

    return subbasins


def _pour_points_from_flowpaths(
    flow_paths: xr.DataArray, flow_acc: xr.DataArray
) -> gpd.GeoSeries:
    """
    Returns outlet cell for each stream
    where the outlet cell is the cell with the maximum flow accumulation value

    Parameters
    ----------
    flow_paths: xr.DataArray
        A raster representing the stream_network, each stream cell is labeled
        by stream_id, non stream cells are 0 or NoData
    flow_acc: xr.DataArray
        A raster representing flow accumulation for each cell

    Returns
    -------
    pour_points: gpd.GeoDataFrame
    """
    pour_points_list = []

    for streamID in finite_unique(flow_paths):
        stream_mask = flow_paths == streamID
        fa_values = np.where(stream_mask, flow_acc.values, np.nan)
        max_idx = np.unravel_index(np.nanargmax(fa_values), fa_values.shape)
        row, col = max_idx
        pour_point = pixel_to_point(flow_paths, row, col)
        pour_points_list.append(pour_point)

    pour_points = gpd.GeoSeries(pour_points_list, crs=flow_paths.rio.crs)
    pour_points = translate_to_wbt(pour_points, flow_paths.rio.resolution())
    return pour_points


def label_subbasins_pour_points(
    flow_dir: xr.DataArray, pour_points: gpd.GeoSeries, wbt: WhiteBoxToolsUnique
) -> xr.DataArray:
    """
    input:
       flow dir
       pour points
    output:
       watersheds
    """
    work_dir = wbt.work_dir
    files = {
        "temp_flowdir": os.path.join(work_dir, f"{wbt.instance_id}-temp_flowdir.tif"),
        "temp_pour_points": os.path.join(
            work_dir, f"{wbt.instance_id}-temp_pour_points.shp"
        ),
        "subbasins": os.path.join(work_dir, f"{wbt.instance_id}-subbasins.tif"),
    }

    flow_dir.rio.to_raster(files["temp_flowdir"])
    pour_points.to_file(files["temp_pour_points"])

    wbt.watershed(
        files["temp_flowdir"],
        files["temp_pour_points"],
        files["subbasins"],
        esri_pntr=False,
    )

    subbasins = rxr.open_rasterio(files["subbasins"], masked=True).squeeze()

    os.remove(files["temp_flowdir"])
    os.remove(files["temp_pour_points"])
    # also remove derivatives
    os.remove(os.path.join(work_dir, f"{wbt.instance_id}-temp_pour_points.shx"))
    os.remove(os.path.join(work_dir, f"{wbt.instance_id}-temp_pour_points.dbf"))
    os.remove(os.path.join(work_dir, f"{wbt.instance_id}-temp_pour_points.prj"))
    os.remove(os.path.join(work_dir, f"{wbt.instance_id}-temp_pour_points.cpg"))
    return subbasins
