import os

import numpy as np
import rioxarray as rxr
import xarray as xr
from whitebox import WhiteboxTools
from pysheds.grid import Grid
from pysheds.view import Raster
from pysheds.view import ViewFinder
from pysheds._sgrid import _angle_to_d8_numba
from pysheds._sgrid import _dinf_hand_iter_numba
from pysheds._sgrid import _assign_hand_heights_numba
from pysheds._sgrid import _mfd_hand_iter_numba


def channel_relief(
    dem: xr.DataArray, flow_paths: xr.DataArray, wbt=None, method="dinf"
) -> xr.DataArray:
    """
    Compute elevation above nearest stream cell (aka HAND)

    Parameters
    ----------
    dem: xr.DataArray
        A raster of elevation values. For d8, dinf, mfd, should be a
        hydrologically conditioned
    flow_paths: xr.DataArray
        A raster of flow paths where cells > 0 are stream
    wbt: optional WhiteboxTools
        An instance of WhiteboxTools class, needed for d8
    method: str
        'd8' wrapper around whiteboxtools elevation above stream method
        'dinf' wrapper around pysheds hand dinf flow routing method
        'mfd' wrapper around pysheds hand mfd flow routing method

    Returns
    -------
    xr.DataArray
        A raster of elevation above nearest stream values
    """
    methods = ["d8, dinf, mfd", "lcp"]
    if method == "d8":
        if wbt is None:
            raise ValueError("wbt must be provided for d8 method")
        hand = hand_steepest(dem, flow_paths, wbt)
    elif method == "dinf":
        hand = hand_pysheds(dem, flow_paths, routing_method="dinf")
    elif method == "mfd":
        hand = hand_pysheds(dem, flow_paths, routing_method="mfd")
    else:
        raise ValueError(f"method needs to be one of {methods}")

    return hand


def hand_steepest(
    dem: xr.DataArray, flow_paths: xr.DataArray, wbt: WhiteboxTools
) -> xr.DataArray:
    """
    Wrapper around elevation above nearest stream WBT method.

    Parameters
    ----------
    dem: xr.DataArray
        A dem that has been hydrologically conditioned
    flow_paths: xr.DataArray
        A raster where nonzero values are flow paths that represent the stream
        path
    wbt: WhiteboxTools
                An instance of the whitebox tools class

    Returns
    -------
    xr.DataArray
        A raster of elevation above stream values
    """
    work_dir = wbt.work_dir
    names = ["temp_conditioned_dem", "temp_flowpaths", "hand"]
    fnames = [os.path.join(work_dir, name + ".tif") for name in names]
    files = {name: file for name, file in zip(names, fnames)}

    # save conditioned and flowpaths to temp files
    dem.rio.to_raster(files["temp_conditioned_dem"])
    flow_paths.rio.to_raster(files["temp_flowpaths"])

    wbt.elevation_above_stream(
        files["temp_conditioned_dem"], files["temp_flowpaths"], files["hand"]
    )

    os.remove(files["temp_conditioned_dem"])
    os.remove(files["temp_flowpaths"])

    try:
        hand = rxr.open_rasterio(files["hand"], masked=True).squeeze()
    except:
        raise ValueError("WhiteboxTools failed to compute HAND")

    return hand


def hand_pysheds(
    dem: xr.DataArray, flow_paths: xr.DataArray, routing_method: str
) -> xr.DataArray:
    """
    Parameters
    ----------
    dem: xr.DataArray
        A hydrologically conditioned DEM
    flow_paths: xr.DataArray
        A raster where nonzero values are flow paths that represent the stream
        path
    routing_method: str
        'dinf' or 'mfd'

    Returns
    -------
    xr.DataArray
        A raster of elevation above stream values
    """

    def xarray_to_pysheds(raster: xr.DataArray) -> Raster:
        view = ViewFinder(
            affine=raster.rio.transform(),
            shape=raster.shape,
            crs=raster.rio.crs,
            nodata=raster.rio.nodata,
        )
        return Raster(raster.data, viewfinder=view)

    pysheds_dem = xarray_to_pysheds(dem)
    pysheds_flowpaths = xarray_to_pysheds(flow_paths)
    grid = Grid.from_raster(pysheds_dem)
    mask = pysheds_flowpaths > 1

    # let pysheds compute flowdir based on routing method
    if routing_method == "dinf":
        fdir = grid.flowdir(pysheds_dem, routing="dinf", nodata_out=np.float64(-1))
        dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
        nodata_cells = grid._get_nodata_cells(fdir)

        fdir_0, fdir_1, prop_0, prop_1 = _angle_to_d8_numba(
            fdir, (64, 128, 1, 2, 4, 8, 16, 32), nodata_cells
        )
        hand_idx = _dinf_hand_iter_numba(fdir_0, fdir_1, mask, dirmap)
    elif routing_method == "mfd":
        fdir = grid.flowdir(pysheds_dem, routing="mfd", nodata_out=np.float64(-1))
        hand_idx = _mfd_hand_iter_numba(fdir, mask)
    else:
        raise ValueError("routing_method must be 'dinf' or 'mfd'")

    hand_raster = _assign_hand_heights_numba(hand_idx, pysheds_dem, np.float64(np.nan))
    hand = dem.copy()
    hand.data = hand_raster
    return hand
