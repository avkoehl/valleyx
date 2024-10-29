"""
    Returns a dataframe of width measurements for a given polygon and its centerline.
"""
import geopandas as gpd

from slopes.geometry.cross_section import get_cross_section_lines
from slopes.geometry.utils import get_length_and_width

def polygon_widths(polygon, centerline, spacing=30):
    """
    Returns a dataframe of width measurements for a given polygon and its centerline. 
    measurments taken at each spacing

    generate cross section lines 
    foreach line, on each side of the centerline, find the closest point on the polygon where it intersects and clip the line
    get width of that clipped line
    """

    # get max dimensions of the polygon and add buffer
    lengths = get_length_and_width(polygon)
    max_len = int(max(lengths) + 200) # 200 is the buffer

    lines = get_cross_section_lines(centerline, xs_spacing=spacing, xs_width=max_len) 
    # a cross section line can intersect the polygon and the centerline multiple times if there is meander
    # so need to iterate through each line, clip it to the polygon and keep only the segment that intersects
    # with the associated origin point on the centerline

    ls = lines.clip(polygon) # this will reorder lines!
    ls = ls.explode(index_parts=False)
    keep = []
    for _,row in ls.iterrows():
        if gpd.GeoSeries(row['geometry']).intersects(row['center_point'].buffer(0.1))[0]:
            keep.append(True)
        else:
            keep.append(False)
    ls = ls.loc[keep]

    # the above code may in rare occasions still result in a duplicated cross section ids
    # in this case its safest just to remove the ids where there are duplicated
    ls = ls[~ls['cross_section_id'].duplicated(keep=False)]

    ls['width'] = ls.length
    ls = ls.sort_values('cross_section_id', ascending=True)

    return ls
