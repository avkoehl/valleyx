"""
Create cross section profiles for given raster(s) and flowlines

inputs:
    flowlines
    raster(s)
    [subbasins]
    line_spacing
    line_width
    point_spacing

outputs:
    lines
    points
"""
from valleyfloor.geometry.cross_section import get_points_on_linestring
from valleyfloor.geometry.cross_ssection import get_cross_section_points_from_points
from valleyfloor.geometry.utils import get_length_and_width

def network_xsections(flowlines, raster, line_spacing, line_width, point_spacing, subbasins=None):
    return
