import os

from numba import njit
import numpy as np
import rioxarray as rxr
import xarray as xr
from whitebox import WhiteboxTools
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from pysheds.grid import Grid
from pysheds.view import Raster
from pysheds.view import ViewFinder
from pysheds._sgrid import _angle_to_d8_numba
from pysheds._sgrid import _dinf_hand_iter_numba
from pysheds._sgrid import _assign_hand_heights_numba
from pysheds._sgrid import _mfd_hand_iter_numba


def hand(dem, flow_paths, wbt=None, method="d8") -> xr.DataArray:
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
        'lcp' least cost path route to nearest stream cell

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
    elif method == "lcp":
        graph = construct_cost_graph(dem)
        hand = hand_cost(dem, flow_paths, graph)
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

    def pysheds_to_rioxarray(raster: Raster, grid: Grid) -> xr.DataArray:
        da = xr.DataArray(
            data=raster,
            dims=["y", "x"],
            coords={
                "y": np.linspace(grid.bbox[3], grid.bbox[1], raster.shape[0]),
                "x": np.linspace(grid.bbox[0], grid.bbox[2], raster.shape[1]),
            },
        )
        da.rio.write_transform(grid.affine, inplace=True)
        da.rio.write_crs(grid.crs, inplace=True)
        da.rio.write_nodata(grid.nodata, inplace=True)
        return da

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
        nodata_cells = grid._get_nodata_cells(fdir)
        hand_idx = _mfd_hand_iter_numba(fdir, mask)
    else:
        raise ValueError("routing_method must be 'dinf' or 'mfd'")

    hand = _assign_hand_heights_numba(hand_idx, pysheds_dem, np.float64(np.nan))
    hand = pysheds_to_rioxarray(hand, grid)
    return hand


def hand_cost(
    dem: xr.DataArray, flow_paths: xr.DataArray, graph: csr_matrix) -> xr.DataArray:
    """
    compute elevation above nearest stream based on a cost graph. Finds the
    stream point with the lowest cost path for each cell. Then detrends from
    the dem and the elevation of that stream point.

    See cost.py module to find examples for making cost graph

    Parameters
    ----------
    dem: xr.DataArray
        A raster of elevation values
    graph: csr_matrix
        A sparse matrix representing the cost graph

    Returns
    -------
    xr.DataArray
        A raster of elevation above stream values
    """

    ids = np.arange(flow_paths.size).reshape(flow_paths.shape)
    source_nodes = ids[flow_paths > 0]

    # get basins
    _, _, basins = dijkstra(
        graph,
        directed=True,
        indices=source_nodes,
        return_predecessors=True,
        min_only=True,
    )
    basins = basins.reshape(dem.shape)

    # get basin elevation values
    stream_elevations = dem.copy()
    stream_elevations.data = np.zeros_like(dem.data)

    for cell_id in np.unique(basins):
        row, col = np.unravel_index(cell_id, basins.shape)
        elev = dem.data[row, col]
        stream_elevations.data[basins == cell_id] = elev

    hand = dem - stream_elevations
    return hand

def construct_cost_graph(dem: xr.DataArray):
	"""
    Parameters
    ----------
    dem: xr.DataArray
        A raster of elevation values

    Returns
    -------
    csr_matrix
        A sparse matrix representing the cost graph
	"""
    values = dem.data
    rows, cols, data = _numba_delta_elevation_cost(values)
    graph = csr_matrix((data, (rows, cols)), shape=(dem.size,dem.size))
    return graph

@njit
def _numba_delta_elevation_cost(dem_data: np.ndarray):
    """
    Parameters
    ----------
    dem_data: np.ndarray
        An array of elevation values

    Returns
    -------
    rows: list
        A list of row indices
    cols: list
        A list of column indices
    data: list
        A list of cost values

    """
    nrows, ncols = dem_data.shape
    ids = np.arange(dem_data.size).reshape(dem_data.shape)
    rows = []
    cols = []
    data = []
    for r in range(nrows):
        for c in range(ncols):
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nr = r + dy
                    nc = c + dx
                    if 0 <= nr < nrows and 0 <= nc <= ncols:
                        cost = np.abs(dem_data[nr, nc] - dem_data[r, c])
                        if np.isfinite(cost):
                            if dx != 0 and dy != 0:
                                cost = cost / 1.41 # diagonal
                            rows.append(ids[r,c])
                            cols.append(ids[nr,nc])
                            data.append(cost)
    return rows, cols, data
