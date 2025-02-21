import xarray as xr
import numpy as np

from valleyx.flow.subbasins import label_subbasins_pour_points
from valleyx.flow.hillslopes import wbt_label_drainage_sides
from valleyx.utils import translate_to_wbt


def reach_subbasins(flowpath_points, flowpaths, flow_dir, wbt):
    whitebox_aligned = translate_to_wbt(flowpath_points, flowpaths.rio.resolution())
    subbasins = label_subbasins_pour_points(flow_dir, whitebox_aligned, wbt)
    copy = subbasins.copy()

    # relabel subbasins
    for sid in np.unique(subbasins):
        if not np.isnan(sid):
            condition = subbasins == sid
            fp = flowpaths.where(condition)
            values = fp.values[np.isfinite(fp.values)]
            value = np.unique(values).item()
            copy.data[condition] = int(value)
    return copy


def reach_hillslopes(subbasins, flowpaths, flowdir, wbt):
    hillslopes = subbasins.copy()
    hillslopes.data = np.full(subbasins.shape, np.nan, dtype=subbasins.dtype)
    for sid in np.unique(subbasins):
        if np.isfinite(sid):
            condition = subbasins == sid
            fp = flowpaths.where(condition)
            fd = flowdir.where(condition)
            hs = wbt_label_drainage_sides(fd, fp, wbt)
            hillslopes = xr.where(hillslopes.isnull(), hs, hillslopes)
    return hillslopes
