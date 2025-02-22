import geopandas as gpd
import numpy as np
from scipy.ndimage import binary_fill_holes

from valleyx.utils.vectorize import single_polygon_from_binary_raster


def valley_bottoms(flowlines, subbasins, hand, threshold):
    stream_ids = np.unique(flowlines.index)
    stream_ids = stream_ids[~np.isnan(stream_ids)]

    bottoms = []
    for stream in stream_ids:
        cropped_hand = hand.where(subbasins == stream, drop=True)
        threshold_hand = cropped_hand < threshold
        threshold_hand.data = binary_fill_holes(threshold_hand.data)
        valley_bottom = single_polygon_from_binary_raster(
            threshold_hand, min_percent_area=90
        )
        bottoms.append((stream, valley_bottom))

    index, bottoms = zip(*bottoms)
    valley_bottoms = gpd.GeoSeries(bottoms, index=index, crs=hand.rio.crs)

    return valley_bottoms
