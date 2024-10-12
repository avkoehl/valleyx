"""
    HAND_steepest as elevation above nearest stream wbt max flow_dir
    HAND_euclidean as elevation above nearest stream based just on euclidean distance
    HAND_dinf as elevation above nearest stream wbt dinfinity flow_dir
    HAND_cost as cost accumulation accumulated change in elevation 

and just a helper function for slope wbt wrapper  (move these to their own functions?)
"""

def detrend(dem, flow_paths, wbt=None, method=""):
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
        graph = cost_graph(dem)
        hand = hand_cost(dem, flow_paths, graph)
    return hand

def hand_steepest(dem: xr.DataArray, flow_paths: xr.DataArray, wbt: WhiteboxTools) -> xr.DataArray():
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
    conditioned_dem.rio.to_raster(files['temp_conditioned_dem'])
    flowpaths.rio.to_raster(files['temp_flowpaths'])

    wbt.elevation_above_stream(
            files['temp_conditioned_dem'],
            files['temp_flowpaths'],
            files['hand'])

    with rxr.open_rasterio(files['hand'], masked=True) as raster:
        hand = raster.squeeze() 

    os.remove(files['temp_conditioned_dem'])
    os.remove(files['temp_flowpaths'])
    return hand

def hand_euclidean(dem: xr.DataArray, flow_paths: xr.DataArray, wbt: WhiteboxTools) -> xr.DataArray():
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

def hand_cost(dem: xr.DataArray, graph: csr_matrix) -> xr.DataArray:
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

    # get basins
    costs, predecessors, basins = dijkstra(graph, source_nodes,
                                           return_predecessors=True,
                                           directed=True, min_only=True)
    basins = basins.reshape(dem.shape)

    # get basin elevation values
    stream_elevations = 

    # subtract basin elevation from each cell in dem to get hand
    hand = dem - stream_elevations + dem.min().item()
    return hand

