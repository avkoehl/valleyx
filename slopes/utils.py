import os
import shutil

import rioxarray as rxr
import geopandas as gpd
import whitebox

def translate_to_wbt(pour_points: gpd.GeoSeries, offset: tuple) -> gpd.GeoSeries:
    """
    Translates a points coordinates from the top left of a cell to the center
    of a cell. 
    """
    return pour_points.translate(xoff=offset[0]/2, yoff=offset[1]/2)

def make_dir(path):
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path)

def setup_wbt(working_dir, verbose=False):
    wbt = whitebox.WhiteboxTools()
    wbt.set_working_dir(os.path.abspath(os.path.expanduser(working_dir)))
    wbt.verbose = verbose
    return wbt


def load_input(dem_path, flowline_path):
    dem = rxr.open_rasterio(dem_path, masked=True).squeeze()
    flowlines = gpd.read_file(flowline_path)
    if flowlines.crs is None:
        flowlines.crs = dem.rio.crs
    return dem, flowlines
