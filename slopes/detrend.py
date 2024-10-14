import os
import sys

import numba
import numpy as np
import rioxarray as rxr
import xarray as xr
from whitebox import WhiteboxTools
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

def detrend(dem, flow_paths, wbt, method="hand_steepest"):
"""
Detrend a digital elevation model by height above nearest drainage
dem should be hydrologically conditioned for steepest, dinf, or cost

4 options for the method:
    HAND_steepest as elevation above nearest stream wbt max flow_dir
    HAND_euclidean as elevation above nearest stream based just on euclidean distance
    HAND_dinf as elevation above nearest stream wbt dinfinity flow_dir
    HAND_cost as cost accumulation accumulated change in elevation 
"""
    method_list = ["hand_steepest", "hand_euclidean", "hand_dinf", "hand_cost"]
    if method not in method_list:
        sys.exit(f"choose valid method from {method_list}")

    if method == "hand_steepest":
        hand = hand_steepest(dem, flow_paths, wbt)
    elif method == "hand_euclidean":
        hand = hand_euclidean(dem, flow_paths, wbt)
    elif method == "hand_dinf":
        sys.exit("not yet implemented")
    elif method == "hand_cost":
        graph = construct_cost_graph(dem)
        hand = hand_cost(dem, flow_paths, graph)

    slope_of_hand = wbt_slope(hand, wbt)
    return hand, slope_of_hand

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
    flow_paths.rio.to_raster(files['flowpaths'])

    wbt.elevation_above_stream_euclidean(
            files['dem'],
            files['flowpaths'],
            files['hand'])

    with rxr.open_rasterio(files['hand'], masked=True) as raster:
        hand = raster.squeeze() 

    os.remove(files['dem'])
    os.remove(files['flowpaths'])
    return hand

def hand_dinf():
    """
    compute elevation above nearest stream using dinf flow direction
    TODO: implement with numba
    """

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
