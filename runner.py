import matplotlib.pyplot as plt
import rioxarray as rxr
import geopandas as gpd
import numpy as np
from shapelysmooth import chaikin_smooth
from shapelysmooth import taubin_smooth

from valleyfloor.process_topography import process_topography
from valleyfloor.utils import setup_wbt

from slopes.subbasins import label_subbasins
from slopes.hillslopes import label_hillslopes
from slopes.network_xsections import network_xsections
from slopes.utils import observe_values
from slopes.preprocess_profile import preprocess_profiles
from slopes.segment_profile import segment_profiles
from slopes.classify_profile import classify_profiles
from slopes.classify_profile_max_ascent import classify_profiles_max_ascent


wbt = setup_wbt("~/opt/WBT", "./working_dir")
dem = rxr.open_rasterio("./data/input/dem.tif", masked=True).squeeze()
flowlines = gpd.read_file("./data/input/flowlines.shp")
flowlines.crs = dem.rio.crs

dataset, aligned_flowlines = process_topography(dem, flowlines, wbt)
aligned_flowlines = gpd.GeoSeries(aligned_flowlines['geometry'].values, index=aligned_flowlines['Stream_ID'])

dataset['subbasin'] = label_subbasins(dataset['flow_dir'], dataset['flow_acc'], dataset['flowpaths'], wbt)
dataset['hillslope'] = label_hillslopes(dataset['flowpaths'], dataset['flow_dir'], dataset['subbasin'], wbt) 

dataset = dataset.rename({'flowpaths': 'flow_path', 'smoothed_dem': 'dem'})

flowlines = []
ids = []
for streamID, linestring in aligned_flowlines.items():
    linestring = linestring.simplify(3)
    linestring = chaikin_smooth(taubin_smooth(linestring))
    ids.append(streamID)
    flowlines.append(linestring)
flowlines = gpd.GeoSeries(flowlines, index=ids, crs=dem.rio.crs)
flowlines.to_file("smoothed.shp")

xsections = network_xsections(flowlines, line_spacing=5,
                              line_width=100, point_spacing=2,
                              subbasins=dataset['subbasin'])

xsections2 = network_xsections(aligned_flowlines, line_spacing=5,
                              line_width=100, point_spacing=2,
                              subbasins=dataset['subbasin'])

profiles = observe_values(xsections, dataset[['flow_path', 'hillslope', 'dem', 'hand', 'slope', 'curvature']])
processed = preprocess_profiles(profiles, min_hand_jump=15, ratio=2.5, min_distance=5)

profiles.crs = dem.rio.crs
processed.crs = dem.rio.crs

# segment profiles
segments = segment_profiles(processed)
classified = classify_profiles(segments)


segments_two = processed.copy()
segments_two['bp'] = processed['curvature'] < -0.01
classified_two = classify_profiles_max_ascent(segments_two, dem, dataset['slope'], 8, 14, wbt)
classified_three = classify_profiles_max_ascent(segments_two, dem, dataset['slope'], 15, 12, wbt)
classified_four = classify_profiles_max_ascent(segments_two, dem, dataset['slope'], 20, 10, wbt)
classified_two.to_file("8cell_14deg.shp")
classified_three.to_file("15cell_12deg.shp")
classified_four.to_file("20cell_10deg.shp")

wps_b = classified_two.loc[classified_two['wallpoint']]
wps_b.to_file('test2.shp')


# hand thresholds  
wps = classified.loc[classified['wallpoint']]
buffer = 2
thresholds = wps.groupby("streamID")['hand'].quantile(.80) # reachID
thresholds = thresholds + buffer



