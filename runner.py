import matplotlib.pyplot as plt
import rioxarray as rxr
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from shapelysmooth import chaikin_smooth
from shapelysmooth import taubin_smooth

from valleyfloor.process_topography import process_topography
from valleyfloor.utils import setup_wbt

from slopes.terrain.subbasins import label_subbasins
from slopes.terrain.hillslopes import label_hillslopes
from slopes.profile.network_xsections import network_xsections
from slopes.utils import observe_values
from slopes.profile.preprocess_profile import preprocess_profiles
from slopes.profile.classify_profile import classify_profiles
from slopes.geometry.centerline import polygon_centerline
from slopes.geometry.width import polygon_widths
from slopes.reach.reaches import delineate_reaches

logger.enable('slopes')


wbt = setup_wbt("~/opt/WBT", "./working_dir")
dem = rxr.open_rasterio("./data/input/dem.tif", masked=True).squeeze()
flowlines = gpd.read_file("./data/input/flowlines.shp")
flowlines.crs = dem.rio.crs

dataset, aligned_flowlines = process_topography(dem, flowlines, wbt)
aligned_flowlines = gpd.GeoSeries(aligned_flowlines['geometry'].values, index=aligned_flowlines['Stream_ID'])

dataset['subbasin'] = label_subbasins(dataset['flow_dir'], dataset['flow_acc'], dataset['flowpaths'], wbt)
dataset['hillslope'] = label_hillslopes(dataset['flowpaths'], dataset['flow_dir'], dataset['subbasin'], wbt) 

dataset = dataset.rename({'flowpaths': 'flow_path', 'smoothed_dem': 'dem'})

dataset, flowlines_reaches = delineate_reaches(dataset, aligned_flowlines, wbt, 200, 30)

smoothed = flowlines_reaches.apply(lambda x: x.simplify(3))
smoothed = flowlines_reaches.apply(lambda x: chaikin_smooth(taubin_smooth(x)))

xsections = network_xsections(smoothed, line_spacing=30,
                              line_width=100, point_spacing=10,
                              subbasins=dataset['subbasins'])

profiles = observe_values(xsections, dataset[['flow_path', 'hillslope', 'dem', 'hand', 'slope', 'curvature']])
processed = preprocess_profiles(profiles, min_hand_jump=15, ratio=2.5, min_distance=5)
classified = classify_profiles(processed, 10)


