"""
given dataframe of wall points
for each point get its upstream neighbor
return geodataframe
geometry, row, col
"""

import pandas as pd
import geopandas as gpd

from valleyx.terrain.flow_dir import DIRMAPS
from valleyx.utils.raster import point_to_pixel
from valleyx.utils.raster import pixel_to_point


def finalize_wallpoints(wall_points, max_ascent_fdir, dirmap=DIRMAPS["wbt"]):
    indices = [point_to_pixel(max_ascent_fdir, point) for point in wall_points]

    results = []
    for row, col in indices:
        direction = max_ascent_fdir[row, col].item()
        new_row = row + dirmap[direction][0]
        new_col = col + dirmap[direction][1]
        point = pixel_to_point(max_ascent_fdir, new_row, new_col)
        results.append({"geometry": point, "row": new_row, "col": new_col})

    df = pd.DataFrame.from_records(results)
    df = gpd.GeoDataFrame(df, geometry="geometry", crs=max_ascent_fdir.rio.crs)
    return df
