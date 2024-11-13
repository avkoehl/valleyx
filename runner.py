import matplotlib.pyplot as plt
import rioxarray as rxr
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from shapelysmooth import chaikin_smooth
from shapelysmooth import taubin_smooth
from loguru import logger
import xarray as xr


from slopes.__main__ import setup_wbt
from slopes.terrain.subbasins import label_subbasins
from slopes.terrain.hillslopes import label_hillslopes
from slopes.profile.network_xsections import network_xsections
from slopes.profile.network_xsections import observe_values
from slopes.profile.preprocess_profile import preprocess_profiles
from slopes.profile.classify_profile import classify_profiles
from slopes.profile.transition_zones import classify_transition_zone
from slopes.geometry.centerline import polygon_centerline
from slopes.geometry.width import polygon_widths
from slopes.reach.reaches import delineate_reaches
from slopes.floor.floor import label_floors
from slopes.max_ascent.classify_profile_max_ascent import classify_profiles_max_ascent
from slopes.terrain.flow_acc import flow_accumulation_workflow
from slopes.terrain.align_flowlines import align_flowlines
from slopes.terrain.surface import elev_derivatives
from slopes.terrain.hand import channel_relief
from slopes.max_ascent.max_ascent import invert_dem
from slopes.terrain.flow_dir import flowdir_wbt

from slopes.utils import setup_wbt
from slopes.flow_analysis import flow_analysis
from slopes.reach_delineation import delineate_reaches
from slopes.wall_detection import detect_wallpoints

logger.enable('slopes')

wbt = setup_wbt("./working_dir")
dem = rxr.open_rasterio("./data/input/dem.tif", masked=True).squeeze()
flowlines = gpd.read_file("./data/input/flowlines.shp")
flowlines.crs = dem.rio.crs

al, ds = flow_analysis(dem, flowlines, wbt)
al_r, ds_r = delineate_reaches(ds, al, wbt, 10, 20, 50, 3)
wp = detect_wallpoints(ds_r, al_r, 1, 10, 100, 3, 20, 5, 10, 4, 5, 10, wbt)

conditioned, flow_dir, flow_acc = flow_accumulation_workflow(dem, wbt)
aligned_flowlines, flowpaths = align_flowlines(flowlines, flow_acc, flow_dir, wbt)
smoothed, slope, curvature = elev_derivatives(conditioned, wbt, sigma=2)
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

inverted_dem = invert_dem(dataset['conditioned_dem'])
max_ascent_fdir = flowdir_wbt(inverted_dem, wbt)


dataset, flowlines_reaches = delineate_reaches(dataset, aligned_flowlines, wbt, 200, 30, minsize=100, window=5)
smoothed = flowlines_reaches.apply(lambda x: x.simplify(3))
smoothed = smoothed.apply(lambda x: chaikin_smooth(taubin_smooth(x)))

#smoothed = aligned_flowlines.apply(lambda x: x.simplify(3))
#smoothed = smoothed.apply(lambda x: chaikin_smooth(taubin_smooth(x)))

#xsections = network_xsections(smoothed, line_spacing=5,
#                              line_width=100, point_spacing=5,
#                              subbasins=dataset['subbasin'])
xsections = network_xsections(smoothed, line_spacing=10,
                              line_width=100, point_spacing=2)


profiles = observe_values(xsections, dataset[['flow_path', 'hillslope', 'dem', 'hand', 'slope', 'curvature']])
processed = preprocess_profiles(profiles, min_hand_jump=15, ratio=5, min_distance=5, min_peak_prominence=10)
classified = classify_transition_zone(processed, 20, 1.5)


classified = classify_profiles(processed, 12, distance=1, height=0.01)
classified.loc[classified['bp']].to_file('bps.shp')
classified_two = classify_profiles_max_ascent(processed, dataset['dem'], dataset['slope'], 15, 12, wbt)
wall_points = classified.loc[classified['wallpoint']]
wall_points_two = classified_two.loc[classified_two['wallpoint']]
wall_points_two.to_file('wp_max_ascent6.shp')
wp2 = finalize_wallpoints(wall_points_two['geom'], max_ascent_fdir)
wp2 = observe_values(wp2, dataset[['hand', 'slope', 'subbasin', 'hillslope', 'flow_path']])
wp2['streamID'] = wp2['subbasin']

floors = label_floors(wp2, dataset, hillslope_threshold=20, plains_threshold=4, buffer=1, min_points=15, percentile=0.80)
#floors = label_floors(wall_points_two, dataset, hillslope_threshold=20, plains_threshold=4, buffer=1, min_points=15, quantile=0.90)
floors.rio.to_raster('floors.tif')
