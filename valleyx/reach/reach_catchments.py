import xarray as xr
import numpy as np


def reach_hillslopes(subbasins, flowpaths, flowdir, ta):
    hillslopes = subbasins.copy()
    hillslopes.data = np.full(subbasins.shape, np.nan, dtype=subbasins.dtype)
    for sid in np.unique(subbasins):
        if np.isfinite(sid):
            condition = subbasins == sid
            fp = flowpaths.where(condition)
            fd = flowdir.where(condition)
            hs = ta.hillslopes(fd, fp)
            hillslopes = xr.where(hillslopes.isnull(), hs, hillslopes)
    return hillslopes
