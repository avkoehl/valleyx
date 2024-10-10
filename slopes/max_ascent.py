"""
"""

def max_ascent_paths(flow_paths: xr.DataArray, graph: csr_matrix, num_points: int):
    """
    Trace paths following the maximum local gradient from the streams.

    Parameters
    ----------
    flow_paths: xr.DataArray
        A raster representing the stream_network, each stream cell is labeled
        by stream_id, non stream cells are 0 or NoData
    graph: csr_matrix
        A directed unweighted graph in csr matrix format where nodes are cells,
        and edges are between that node and the neighboring cell with maximum
        positive elevation change.
    num_points: int
        The number of points to sample from each stream in the flowpaths raster

    Returns
    -------
    gpd.GeoDataFrame:
        Points representing the paths with the following columns:
            - "geometry": Point
            - "streamID": streamID path starts on
            - "pathID": streamID path starts on
            - "pointID": streamID path starts on
    """
    pass

def create_max_ascent_graph_wbt(dem: xr.DataArray, wbt: WhiteboxTools):
    """
    Connects every cell with its max elevation change neighbor. 
    Given elevation raster, invert: -1 * (dem - max_elev) + min_value
    Run whiteboxtools d8 flowdir
    flowdir to graph
    """
    pass

def create_max_ascent_graph_numba(dem: xr.DataArray):
    """
    Connects every cell with its max elevation change neighbor. 
    iterate through each cell, add edge to neighbor of positive max elevation change
    create csgraph
    """

