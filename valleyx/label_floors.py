import numpy as np
from scipy.ndimage import binary_fill_holes
from loguru import logger

from valleyx.floor.foundation import foundation
from valleyx.floor.connect import connected
from valleyx.raster.raster_utils import finite_unique

logger.bind(module="label_floors")


def check_dataset(dataset):
    required = ["hand", "slope", "subbasin", "hillslope", "flow_path"]
    for key in required:
        if key not in dataset:
            raise ValueError(f"raster missing in dataset: {key}")


def label_floors(
    wall_points,
    dataset,
    max_floor_slope,
    foundation_threshold,
    buffer,
    min_points,
    percentile,
):
    logger.info("Starting label floors process")
    check_dataset(dataset)

    floors = dataset["subbasin"].copy()
    floors.data = np.full(floors.shape, False, dtype=bool)

    logger.debug(f"Detecting baseline floor with slope threshold: {foundation_threshold}")
    foundation_floor = foundation(
        dataset["slope"], dataset["flow_path"], foundation_threshold
    )

    for i, streamID in enumerate(finite_unique(dataset["subbasin"])):
        clipped_data = dataset.where(dataset["subbasin"] == streamID)

        points = wall_points.loc[wall_points["streamID"] == streamID]

        if points is not None:
            logger.debug(
                    f"{streamID}, count: {i} of {len(finite_unique(dataset['subbasin']))}, points: {len(points)}"
                    )
            floor = subbasin_floor(
                points,
                clipped_data["slope"],
                clipped_data["hillslope"],
                clipped_data["hand"],
                max_floor_slope,
                min_points,
                buffer,
                percentile,
            )
            floors = floors | floor
        else:
            logger.debug(
                    f"{streamID}, count: {i} of {len(finite_unique(dataset['subbasin']))}, points: 0"
                    )
            continue  # no fkoor for subbasin other than the foundation

    # 0 = not floor, 1 = flowpath, 2 = base, 3 = added
    combined = floors.copy()
    combined.data = np.zeros_like(floors)
    combined = combined.astype(np.uint8)
    combined.data[floors] = 3
    combined.data[foundation_floor] = 2
    combined.data[dataset["flow_path"] > 0] = 1

    # keep only cells with connectivity to the flowpaths
    result = connected((combined > 0), dataset["flow_path"])
    combined.data[~result] = 0

    logger.success("Finished label floors process")
    return combined


def subbasin_floor(
    all_wall_points,
    slope,
    hillslopes,
    hand,
    max_floor_slope,
    min_points,
    buffer,
    percentile,
):
    """
    Get valley floor for single subbasin given clipped input data
    Logic:

    for each hillslope:
        if enough valley wall points:
            apply hand_threshold method
        else (not enough valley wall points):
            skip
    union of all boolean rasters
    """
    unique_hillslopes = np.unique(hillslopes)
    unique_hillslopes = unique_hillslopes[np.isfinite(unique_hillslopes)]

    hs_floor_masks = []
    for hillslope in unique_hillslopes:
        if hillslope == 0:
            continue

        points = all_wall_points.loc[all_wall_points["hillslope"] == hillslope]
        if len(points) >= min_points:
            h_hand = hand.where(hillslopes == hillslope)
            h_slope = slope.where(hillslopes == hillslope)
            hand_threshold = np.quantile(points["hand"], percentile)
            hand_threshold += buffer
            hs_floor = hand_threshold_floor(
                h_hand, h_slope, hand_threshold, max_floor_slope
            )
            # print('\t\t hand threshold:', hand_threshold,  hs_floor.sum().item())
            hs_floor_masks.append(hs_floor)
        else:
            continue

    if len(hs_floor_masks):
        union = np.logical_or.reduce(hs_floor_masks)
        filled = binary_fill_holes(union.astype(int))
        floor = slope.copy()
        floor.data = filled
        floor = floor.astype(bool)
    else:
        floor = slope.copy()
        floor.data = np.full_like(slope.data, False)
        floor = floor.astype(bool)
    return floor


def hand_threshold_floor(hand, slope, hand_threshold, slope_threshold):
    hand_condition = hand <= hand_threshold
    if slope_threshold is None:
        return hand_condition
    else:
        slope_condition = slope <= slope_threshold
        combined = hand_condition & slope_condition
        return combined

def subbasin_floors(floor, subbasins):
    result = floor.copy()
    floor_condition = floor > 0
    for subbasinID in finite_unique(subbasins):
        condition = subbasins.data == subbasinID
        result.data[floor_condition & condition] = subbasinID
    return result
