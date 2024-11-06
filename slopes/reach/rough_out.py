import geopandas as gpd
import numpy as np
from scipy.ndimage import binary_fill_holes

from slopes.raster.vectorize import single_polygon_from_binary_raster

def rough_out_hand(subbasins, hand, threshold):
    stream_ids = np.unique(subbasins)
    stream_ids = stream_ids[~np.isnan(stream_ids)]

    floors = []
    for stream in stream_ids:
        # valley floor
        cropped_hand = hand.where(subbasins == stream, drop=True)
        threshold_hand = cropped_hand < threshold
        threshold_hand.data = binary_fill_holes(threshold_hand.data)
        valley_floor = single_polygon_from_binary_raster(threshold_hand, min_percent_area=90)
        floors.append((stream, valley_floor))

    index, floors = zip(*floors)
    valley_floors = gpd.GeoSeries(floors, index=index, crs=hand.rio.crs)

    return valley_floors
