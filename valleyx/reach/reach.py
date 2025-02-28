import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from loguru import logger

from valleyx.tools.centerline import polygon_centerline
from valleyx.reach.valley_bottoms import valley_bottoms
from valleyx.reach.segment import segment_reaches
from valleyx.reach.relabel_flowpaths import relabel_flowpaths
from valleyx.reach.reach_catchments import reach_hillslopes
from valleyx.utils.flowpaths import prep_flowlines

logger.bind(module="delineate_reaches")


def delineate_reaches(basin, ta, hand_threshold, spacing, minsize, window):
    """
    hand_threshold : float
            Maximum elevation above nearest drainage for valley floor delineation
    spacing : float
            Spacing in distance to sample width measurements at
    minsize : float
            Minimum reach length
    window : int
            Window size for smoothing the width series in number of samples
    """
    logger.info("Starting delineate reaches processing")
    logger.debug("estimate valley bottoms")
    vbs = valley_bottoms(basin.flowlines, basin.subbasins, basin.hand, hand_threshold)

    logger.debug("Split segments into reaches")
    pour_points = []
    for streamID in basin.flowlines.index:
        bottom = vbs.loc[streamID]
        flowline = basin.flowlines.loc[streamID]
        inlet = Point(flowline.coords[0])
        outlet = Point(flowline.coords[-1])
        centerline = polygon_centerline(bottom, 500, inlet, outlet, 5, 100, True)

        if centerline is None:
            centerline = flowline

        reach_points = segment_reaches(
            bottom,
            centerline,
            flowline,
            basin.flow_paths == streamID,
            basin.flow_acc,
            spacing,
            window,
            minsize,
        )
        reach_points = gpd.GeoDataFrame(geometry=reach_points)
        reach_points["streamID"] = streamID
        logger.debug(
            f"streamID: {streamID} of {len(vbs)} - {len(reach_points)} reaches"
        )
        pour_points.append(reach_points)

    pour_points = pd.concat(pour_points, ignore_index=True)

    # need to relabel flowpaths
    basin.flow_paths = relabel_flowpaths(pour_points, basin.flow_paths, basin.flow_acc)
    basin.flowlines = prep_flowlines(
        ta.flowpaths_to_flowlines(basin.flow_paths, basin.flow_dir), basin.flow_acc
    )
    basin.subbasins = ta.subbasins(basin.flow_dir, pour_points)
    basin.hillslopes = reach_hillslopes(
        basin.subbasins, basin.flow_paths, basin.flow_dir, ta
    )

    logger.debug(f"Number of input flowline segments: {len(vbs)}")
    logger.debug(f"Number of reaches: {len(basin.flowlines)}")
    logger.success("Delineate reaches successfully completed")
    return basin
