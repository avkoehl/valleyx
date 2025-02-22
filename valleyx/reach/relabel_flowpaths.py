import numpy as np
import geopandas as gpd

from valleyx.utils.raster import pixel_to_point, point_to_pixel


def relabel_flowpaths(pour_points, flowpaths, flowacc):
    # get the cell ids of the pour points
    cells = _flowpath_cells(flowpaths, flowacc)
    pour_points = _add_cell_id(pour_points, flowacc)
    cell_ids = pour_points["cell_id"]

    cells = _assign_reach_id(cells, cell_ids)

    new_flowpaths = flowpaths.copy()
    for label, inds in cells.groupby("reach_id").groups.items():
        rows = cells["row"].loc[inds].values
        cols = cells["col"].loc[inds].values
        new_flowpaths.values[rows, cols] = label
    return new_flowpaths


def _add_cell_id(pour_points, flowacc):
    id_grid = np.arange(flowacc.size).reshape(flowacc.shape)
    cids = []
    for point in pour_points["geometry"]:
        row, col = point_to_pixel(flowacc, point)
        cid = id_grid[row, col]
        cids.append(cid)
    pour_points["cell_id"] = cids
    return pour_points


def _flowpath_cells(flowpath, flowacc):
    """
    for each cell in flowpath get the flow accumulation, its id, its coordinate, its x, its y
    sort by flowacc
    """
    condition = np.isfinite(flowpath)

    id_grid = np.arange(flowpath.size).reshape(flowpath.shape)
    stream_points = id_grid[condition]
    fa_values = flowacc.data[condition]
    path_values = flowpath.data[condition]
    rows, cols = np.where(condition)

    coordinates = [pixel_to_point(flowacc, row, col) for row, col in zip(rows, cols)]

    df = gpd.GeoDataFrame(
        {
            "segment_id": path_values,
            "cell_id": stream_points,
            "flow_acc": fa_values,
            "geometry": coordinates,
            "row": rows,
            "col": cols,
        },
        geometry="geometry",
        crs=flowpath.rio.crs,
    )

    # sort by flow_acc and segment_id
    sorted = df.sort_values(["segment_id", "flow_acc"])
    return sorted


def _assign_reach_id(flowpath_cells, bp_cell_ids):
    reach_ids = []
    reach = 0
    for cell_id in flowpath_cells["cell_id"]:
        reach_ids.append(reach)
        if cell_id in bp_cell_ids.values:
            reach += 1

    flowpath_cells["reach_id"] = reach_ids
    return flowpath_cells
