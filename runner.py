import matplotlib.pyplot as plt
import rioxarray as rxr
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from shapelysmooth import chaikin_smooth
from shapelysmooth import taubin_smooth

from valleyfloor.process_topography import process_topography
from valleyfloor.utils import setup_wbt

from slopes.subbasins import label_subbasins
from slopes.hillslopes import label_hillslopes
from slopes.network_xsections import network_xsections
from slopes.utils import observe_values
from slopes.preprocess_profile import preprocess_profiles
from slopes.classify_profile import classify_profiles
from slopes.classify_profile_max_ascent import classify_profiles_max_ascent
from slopes.rough_out import rough_out_hand


wbt = setup_wbt("~/opt/WBT", "./working_dir")
dem = rxr.open_rasterio("/Users/arthurkoehl/programs/pasternack/ca-river-valleys/data/180500050303/180500050303-dem.tif", masked=True).squeeze()
flowlines = gpd.read_file("~/programs/pasternack/ca-river-valleys/data/180500050303/180500050303-flowlines.shp")
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

xsections = network_xsections(flowlines, line_spacing=30,
                              line_width=100, point_spacing=10,
                              subbasins=dataset['subbasin'])


profiles = observe_values(xsections, dataset[['flow_path', 'hillslope', 'dem', 'hand', 'slope', 'curvature']])
processed = preprocess_profiles(profiles, min_hand_jump=15, ratio=2.5, min_distance=5)

classified = classify_profiles(processed, 10)
classified_two = classify_profiles_max_ascent(processed, dem, dataset['slope'], 6, 10, wbt)


# hand thresholds  
wps = classified.loc[classified['wallpoint']]
wps_two = classified_two.loc[classified_two['wallpoint']]

thresholds = wps.groupby("streamID")['hand'].quantile(.80) # reachID
thresholds

thresholds2 = wps_two.groupby("streamID")['hand'].quantile(.80) # reachID
thresholds2



# rough out valley floors
vfs = rough_out_hand(dataset['subbasin'], dataset['hand'], 10)
inds = []
lines = []
for index,vf in vfs.items():
    print(index)
    flowline = aligned_flowlines.loc[index]
    source = Point(flowline.coords[0])
    target = Point(flowline.coords[-1])
    centerline = polygon_centerline(vf, 200, source=source, target=target, simplify_tolerance=5, dist_tolerance = 100, smooth_output=True)
    inds.append(index)
    lines.append(centerline)

results = gpd.GeoSeries(lines, index=inds, crs=dataset['subbasin'].rio.crs)



