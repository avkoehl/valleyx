import numba
from numba.typed import Dict
import numpy as np
import geopandas as gpd
import rioxarray
import xarray as xr

DIRMAPS = {
    "esri": {
        32: (-1, -1),  # up left
        64: (-1, 0),  # up
        128: (-1, 1),  # up right
        16: (0, -1),  # left
        0: (0, 0),  # stay (terminal cell)
        1: (0, 1),  # right
        8: (1, -1),  # down left
        4: (1, 0),  # down
        2: (1, 1),  # down right
    },
    "wbt": {
        64: (-1, -1),  # up left
        128: (-1, 0),  # up
        1: (-1, 1),  # up right
        32: (0, -1),  # left
        0: (0, 0),  # stay (terminal cell)
        2: (0, 1),  # right
        16: (1, -1),  # down left
        8: (1, 0),  # down
        4: (1, 1),  # down right
    },
}


@numba.njit
def _trace_flowpath_numba(current_row, current_col, flow_dir_values, dirmap, num_cells):
    nrows, ncols = flow_dir_values.shape
    path = [(current_row, current_col)]
    count = 0
    while True:
        if num_cells > 0:
            if count >= num_cells:
                break

        current_direction = flow_dir_values[current_row, current_col]
        if current_direction == 0:
            break

        drow, dcol = dirmap[current_direction]
        next_row = current_row + drow
        next_col = current_col + dcol

        if not (0 <= next_row < nrows and 0 <= next_col < ncols):
            break

        current_row, current_col = next_row, next_col
        path.append((next_row, next_col))
        count = count + 1
    return path


def trace_flowpath(
    row: int,
    col: int,
    flow_dir: xr.DataArray,
    dirmap: dict,
    num_cells: int,
) -> gpd.GeoSeries:
    """
    Traces the flowpath from a given cell.

    Parameters
    ----------
    row: int
        Row index
    col: int
        Column index
    flow_dir: xr.DataArray
        A raster representing the flowdirections
    dirmap: dict
        Direction mappings
    num_cells: int
        if -1 then get full path, else stop path after traversing num_cells

    Returns
    -------
    (gpd.GeoSeries, list)
        - Series of point geometries representing the path
        - list of cell (row, col)

    """
    d = Dict()  # numba typed dict
    for k, v in dirmap.items():
        d[np.float32(k)] = np.int64(v)

    path = _trace_flowpath_numba(
        np.int64(row), np.int64(col), flow_dir.values, d, num_cells
    )

    return path
