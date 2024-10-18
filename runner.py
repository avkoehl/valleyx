import matplotlib.pyplot as plt
import rioxarray as rxr
import geopandas as gpd
import numpy as np

from valleyfloor.process_topography import process_topography
from valleyfloor.utils import setup_wbt

from slopes.subbasins import label_subbasins
from slopes.hillslopes import label_hillslopes
from slopes.network_xsections import network_xsections
from slopes.utils import observe_values


wbt = setup_wbt("~/opt/WBT", "./working_dir")
dem = rxr.open_rasterio("./data/input/dem.tif", masked=True).squeeze()
flowlines = gpd.read_file("./data/input/flowlines.shp")
flowlines.crs = dem.rio.crs

dataset, aligned_flowlines = process_topography(dem, flowlines, wbt)
aligned_flowlines = gpd.GeoSeries(aligned_flowlines['geometry'].values, index=aligned_flowlines['Stream_ID'])

dataset['subbasin'] = label_subbasins(dataset['flow_dir'], dataset['flow_acc'], dataset['flowpaths'], wbt)
dataset['hillslope'] = label_hillslopes(dataset['flowpaths'], dataset['flow_dir'], dataset['subbasin'], wbt) 

dataset = dataset.rename({'flowpaths': 'flow_path', 'smoothed_dem': 'dem'})

xsections = network_xsections(aligned_flowlines, line_spacing=10,
                              line_width=100, point_spacing=3,
                              subbasins=dataset['subbasin'])

profiles = observe_values(xsections, dataset[['flow_path', 'hillslope', 'dem', 'hand']])

streamID = 6
xsID = 4
profile = profiles.loc[(profiles['streamID'] == streamID) & (profiles['xsID'] == xsID)]
