from dataclasses import dataclass

import xarray as xr
import geopandas as gpd


@dataclass
class BasinData:
    dem: xr.DataArray
    flowlines: gpd.GeoSeries

    conditioned_dem: xr.DataArray
    flow_paths: xr.DataArray
    flow_dir: xr.DataArray
    flow_acc: xr.DataArray

    subbasins: xr.DataArray
    hillslopes: xr.DataArray

    hand: xr.DataArray
