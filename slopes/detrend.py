import os
import sys

import numba
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

from valleyfloor.utils import setup_wbt

dem = rxr.open_rasterio("../working_dir/conditioned_dem.tif", masked=True).squeeze()
flow_paths = rxr.open_rasterio("../working_dir/flowpaths.tif", masked=True).squeeze()
wbt = setup_wbt("~/opt/WBT", "../working_dir")

def detrend(dem, flow_paths, wbt, method="hand_steepest"):
"""
Detrend a digital elevation model by height above nearest drainage
dem should be hydrologically conditioned for steepest, dinf, mfd, or cost

Parameters
----------
dem: xr.DataArray
flow_paths: xr.DataArray
wbt: WhiteboxTools
method: str
    'HAND_steepest' as elevation above nearest stream wbt max flow_dir
    'HAND_euclidean' as elevation above nearest stream based just on euclidean distance
    'HAND_dinf' as elevation above nearest stream dinfinity flow dir
    'HAND_multi' as elevation above nearest stream mfd flow dir
    'HAND_cost' as cost accumulation accumulated change in elevation 

Returns
-------
tuple(xr.DataArray, xr.DataArray) - hand and slope of hand
"""
    method_list = ["hand_steepest", "hand_euclidean", "hand_dinf", "hand_multi", "hand_cost"]
    if method not in method_list:
        sys.exit(f"choose valid method from {method_list}")

    if method == "hand_steepest":
        hand = hand_steepest(dem, flow_paths, wbt)
    elif method == "hand_euclidean":
        raise NotImplementedError("have not thought this one through")
        hand = hand_euclidean(dem, flow_paths, wbt)
    elif method == "hand_dinf":
        hand = hand_pysheds(dem, flow_paths, routing_method='dinf')
    elif method == "hand_multi":
        hand = hand_pysheds(dem, flow_paths, routing_method='mfd')
    elif method == "hand_cost":
        graph = construct_cost_graph(dem)
        hand = hand_cost(dem, flow_paths, graph)

    slope_of_hand = wbt_slope(hand, wbt)
    return (hand, slope_of_hand)

def hand_steepest(dem: xr.DataArray, flow_paths: xr.DataArray, wbt: WhiteboxTools) -> xr.DataArray:
    """ 
    Wrapper around elevation above nearest stream WBT method.

    Parameters
    ----------

    dem: xr.DataArray
        A dem that has been hydrologically conditioned
    flow_paths: xr.DataArray
        A raster where nonzero values are flow paths that represent the stream path
    wbt: WhiteboxTools
		An instance of the whitebox tools class
    """
    work_dir = wbt.work_dir
    names = ['temp_conditioned_dem', 'temp_flowpaths', 'hand']
    fnames = [os.path.join(work_dir, name + '.tif') for name in names]
    files = {name:file for name,file in zip(names,fnames)}

    # save conditioned and flowpaths to temp files
    dem.rio.to_raster(files['temp_conditioned_dem'])
    flow_paths.rio.to_raster(files['temp_flowpaths'])

    wbt.elevation_above_stream(
            files['temp_conditioned_dem'],
            files['temp_flowpaths'],
            files['hand'])

    with rxr.open_rasterio(files['hand'], masked=True) as raster:
        hand = raster.squeeze() 

    os.remove(files['temp_conditioned_dem'])
    os.remove(files['temp_flowpaths'])
    return hand

def hand_euclidean(dem: xr.DataArray, flow_paths: xr.DataArray, wbt: WhiteboxTools) -> xr.DataArray:
    """ 
    Wrapper around elevation above nearest stream euclidean WBT method.

    Parameters
    ----------

    dem: xr.DataArray
        A dem that has been hydrologically conditioned
    flow_paths: xr.DataArray
        A raster where nonzero values are flow paths that represent the stream path
    wbt: WhiteboxTools
		An instance of the whitebox tools class

    Returns
    -------
    xr.DataArray
        A dem of elevation above stream

    """
    files = {'dem': os.path.join(wbt.work_dir, 'temp_dem.tif'),
             'flowpaths': os.path.join(wbt.work_dir, 'temp_flowpaths.tif'),
             'hand': os.path.join(wbt.work_dir, 'hand_e.tif')}

    dem.rio.to_raster(files['dem'])

    # see https://github.com/jblindsay/whitebox-tools/issues/245 
    (flow_paths > 1).astype(np.uint8).rio.to_raster(files['flowpaths'])
    #flow_paths.rio.to_raster(files['flowpaths'])

    wbt.elevation_above_stream_euclidean(
            files['dem'],
            files['flowpaths'],
            files['hand'])

    with rxr.open_rasterio(files['hand'], masked=True) as raster:
        hand = raster.squeeze() 

    os.remove(files['dem'])
    os.remove(files['flowpaths'])
    return hand

def hand_pysheds(dem, flow_paths, routing_method):
    """
    conditioned dem
    compute elevation above nearest stream using dinf flow direction
    # use pysheds
    """
    def xarray_to_pysheds(raster: xr.DataArray) -> Raster:
        view = ViewFinder(affine=raster.rio.transform(), shape=raster.shape, crs=raster.rio.crs, nodata=raster.rio.nodata)
        return Raster(raster.data, viewfinder=view)

    def pysheds_to_rioxarray(raster: Raster, grid: Grid) -> xr.DataArray:
        da = xr.DataArray(
                data = raster,
                dims = ['y','x'],
                coords = {
                    "y": np.linspace(
                        grid.bbox[3], grid.bbox[1], raster.shape[0]),
                    "x": np.linspace(
                        grid.bbox[0], grid.bbox[2], raster.shape[1])
                    }
                )
        da.rio.write_transform(grid.affine, inplace=True)
        da.rio.write_crs(grid.crs.to_string(), inplace=True)
        da.rio.write_nodata(grid.nodata, inplace=True)
        return da

    pysheds_dem = xarray_to_pysheds(dem)
    pysheds_flowpaths = xarray_to_pysheds(flow_paths)
    grid = Grid.from_raster(pysheds_dem)
    mask = pysheds_flow_paths > 1

    # let pysheds compute flowdir based on routing method
    if routing_method == 'dinf':
        fdir = grid.flowdir(pysheds_dem, routing='dinf', nodata_out=np.float64(-1))
        dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
        nodata_cells = grid._get_nodata_cells(fdir)

        fdir_0, fdir_1, prop_0, prop_1 = _angle_to_d8_numba(fdir, (64,128,1,2,4,8,16,32), nodata_cells)
        dirleft_0, dirright_0, dirtop_0, dirbottom_0 = grid._pop_rim(fdir_0,nodata=0)
        dirleft_1, dirright_1, dirtop_1, dirbottom_1 = grid._pop_rim(fdir_1,nodata=0)
        maskleft, maskright, masktop, maskbottom = grid._pop_rim(mask, nodata=False)
        hand_idx = _dinf_hand_iter_numba(fdir_0, fdir_1, mask, dirmap)
    elif routing_method == 'mfd':
        fdir = grid.flowdir(pysheds_dem, routing='mfd', nodata_out=np.float64(-1))
        nodata_cells = grid._get_nodata_cells(fdir)
        dirleft, dirright, dirtop, dirbottom = grid._pop_rim(fdir, nodata=0.)
        maskleft, maskright, masktop, maskbottom = grid._pop_rim(mask, nodata=False)
        hand_idx = _mfd_hand_iter_numba(fdir, mask)
    else:
        raise ValueError("routing_method must be 'dinf' or 'mfd'")


    hand = _assign_hand_heights_numba(hand_idx, pysheds_dem, np.float64(np.nan))
    hand = pysheds_to_rioxarray(hand, grid)
    return hand

def hand_cost(dem: xr.DataArray, flow_paths: xr.DataArray,  graph: csr_matrix) -> xr.DataArray:
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
        A raster of detrended elevations
    """

    ids = np.arange(flow_paths.size).reshape(flow_paths.shape)
    source_nodes = ids[flow_paths > 0]

    # get basins
    costs, predecessors, basins = dijkstra(graph, directed=True, indices=source_nodes,
                                           return_predecessors=True,
                                            min_only=True)
    basins = basins.reshape(dem.shape)

    # get basin elevation values
    stream_elevations = dem.copy()
    stream_elevations.data = np.zeros_like(dem.data)

    for cell_id in np.unique(basins):
        row, col = np.unravel_index(cell_id, basins.shape)
        elev = dem.data[row, col]
        stream_elevations.data[basins == cell_id] = elev

    # subtract basin elevation from each cell in dem to get hand
    hand = dem - stream_elevations + dem.min().item()
    return hand


def wbt_slope(dem: xr.DataArray, wbt: WhiteboxTools) -> xr.DataArray:
    """
    compute slope of surface, wrapper around wbt

    Parameters
    ----------
    dem: xr.DataArray
        A raster of elevation values

    Returns
    -------
    xr.DataArray
        A raster of slope values in degrees
    """
    files ={
            'dem': os.path.join(wbt.work_dir, 'temp_dem.tif'),
            'slope': os.path.join(wbt.work_dir, 'hslope.tif')}
    dem.rio.to_raster(files['dem'])

    wbt.slope(files['dem'], files['slope'], units='degrees')

    with rxr.open_rasterio(files['slope'], masked=True) as raster:
        slope_of_hand = raster.squeeze().copy()

    os.remove(files['dem'])
    return slope_of_hand

def construct_cost_graph(dem: xr.DataArray) -> csr_matrix:
    rows, cols, data = _numba_delta_elevation_cost(dem.data) # row is id of source, col is id of target, data is 1
    graph = csr_matrix((data, (rows, cols)), shape=(dem.size,dem.size))
    return graph

@numba.njit
def _numba_delta_elevation_cost(dem_data: np.ndarray):
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
