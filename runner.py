import matplotlib.pyplot as plt
import rioxarray as rxr
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from shapelysmooth import chaikin_smooth
from shapelysmooth import taubin_smooth
from loguru import logger
import xarray as xr

from valleyfloor.utils import setup_wbt

from slopes.terrain.subbasins import label_subbasins
from slopes.terrain.hillslopes import label_hillslopes
from slopes.profile.network_xsections import network_xsections
from slopes.profile.network_xsections import observe_values
from slopes.profile.preprocess_profile import preprocess_profiles
from slopes.profile.classify_profile import classify_profiles
from slopes.geometry.centerline import polygon_centerline
from slopes.geometry.width import polygon_widths
from slopes.reach.reaches import delineate_reaches
from slopes.floor.floor import label_floors
from slopes.max_ascent.classify_profile_max_ascent import classify_profiles_max_ascent
from slopes.terrain.flow_acc import flow_accumulation_workflow
from slopes.terrain.align_flowlines import align_flowlines
from slopes.terrain.surface import elev_derivatives
from slopes.terrain.hand import channel_relief

logger.enable('slopes')

wbt = setup_wbt("~/opt/WBT", "./working_dir")
dem = rxr.open_rasterio("./data/input/dem.tif", masked=True).squeeze()
flowlines = gpd.read_file("./data/input/flowlines.shp")
flowlines.crs = dem.rio.crs

conditioned, flow_dir, flow_acc = flow_accumulation_workflow(dem, wbt)
aligned_flowlines, flowpaths = align_flowlines(flowlines, flow_acc, flow_dir, wbt)
smoothed, slope, curvature = elev_derivatives(conditioned, wbt, sigma=.75)
hand = channel_relief(conditioned, flowpaths, wbt, method='d8')

dataset = xr.Dataset()
dataset['conditioned_dem'] = conditioned
dataset['flow_dir'] = flow_dir
dataset['flow_acc'] = flow_acc
dataset['flow_path'] = flowpaths
dataset['hand'] = hand
dataset['dem'] = smoothed
dataset['slope'] = slope
dataset['curvature'] = curvature

dataset['subbasin'] = label_subbasins(dataset['flow_dir'], dataset['flow_acc'], dataset['flow_path'], wbt)
dataset['hillslope'] = label_hillslopes(dataset['flow_path'], dataset['flow_dir'], dataset['subbasin'], wbt) 


dataset, flowlines_reaches = delineate_reaches(dataset, aligned_flowlines, wbt, 200, 30, minsize=100, window=5)
smoothed = flowlines_reaches.apply(lambda x: x.simplify(3))
smoothed = smoothed.apply(lambda x: chaikin_smooth(taubin_smooth(x)))

#smoothed = aligned_flowlines.apply(lambda x: x.simplify(3))
#smoothed = smoothed.apply(lambda x: chaikin_smooth(taubin_smooth(x)))

#xsections = network_xsections(smoothed, line_spacing=5,
#                              line_width=100, point_spacing=5,
#                              subbasins=dataset['subbasin'])
xsections = network_xsections(smoothed, line_spacing=5,
                              line_width=100, point_spacing=5)


profiles = observe_values(xsections, dataset[['flow_path', 'hillslope', 'dem', 'hand', 'slope', 'curvature']])
processed = preprocess_profiles(profiles, min_hand_jump=15, ratio=5, min_distance=5, min_peak_prominence=10)
classified = classify_profiles(processed, 12, distance=1, height=0.01)
classified.loc[classified['bp']].to_file('bps.shp')
classified_two = classify_profiles_max_ascent(processed, dataset['dem'], dataset['slope'], 6, 12, wbt)
wall_points = classified.loc[classified['wallpoint']]
wall_points_two = classified_two.loc[classified_two['wallpoint']]
wall_points_two.to_file('wp_max_ascent.shp')

floors = label_floors(wall_points_two, dataset, hillslope_threshold=20, plains_threshold=4, buffer=1, min_points=15, quantile=0.90)
#floors = label_floors(wall_points_two, dataset, hillslope_threshold=20, plains_threshold=4, buffer=1, min_points=15, quantile=0.90)
floors.rio.to_raster('floors.tif')
