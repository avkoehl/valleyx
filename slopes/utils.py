import os
import shutil

import geopandas as gpd

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
