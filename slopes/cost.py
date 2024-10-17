from numba import njit
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
import xarray as xr


def flow_paths_cost_accumulation(
    flow_paths: xr.DataArray, graph: csr_matrix
) -> xr.DataArray:
    """
    Compute accumulated cost to get to each point from the flow_paths

    See construct_cost_graph for an example of how to make a cost graph

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

    costs, _, _ = dijkstra(
        graph,
        directed=True,
        indices=source_nodes,
        return_predecessors=True,
        min_only=True,
    )
    costs = costs.reshape(flow_paths.shape)

    costs_raster = flow_paths.copy()
    costs_raster.data = costs

    return costs_raster


def construct_cost_graph(dem: xr.DataArray) -> csr_matrix:
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
    graph = csr_matrix((data, (rows, cols)), shape=(dem.size, dem.size))
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
                                cost = cost / 1.41  # diagonal
                            rows.append(ids[r, c])
                            cols.append(ids[nr, nc])
                            data.append(cost)
    return rows, cols, data
