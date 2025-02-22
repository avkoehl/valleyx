import xarray as xr
import pandas as pd

from valleyx.floor.flood_extent.preprocess_profile import preprocess_profiles
from valleyx.floor.smooth import filter_nan_gaussian_conserving
from valleyx.tools.network_xsections import observe_values
from valleyx.tools.network_xsections import network_xsections
from valleyx.utils.raster import finite_unique


def flood(
    basin,
    ta,
    sigma,
    line_spacing,
    line_width,
    line_max_width,
    point_spacing,
    min_hand_jump,
    ratio,
    min_peak_prominence,
    min_distance,
    num_cells,
):
    # create cross section profiles
    dataset = prep_data(basin, ta, sigma)
    xsections = network_xsections(
        smooth_flowlines(basin.flowlines),
        line_spacing,
        line_width,
        point_spacing,
        line_max_width,
        basin.subbasins,
    )
    xsections = observe_values(xsections, dataset)

    # preprocess cross section profiles
    profiles = preprocess_profiles(
        xsections,
        min_hand_jump,
        ratio,
        min_distance,
        min_peak_prominence,
    )
    # detect boundary points
    xsections = classify_profiles_max_ascent(
        xsections,
        basin.conditioned_dem,
        dataset["slope"],
        num_cells,
        slope_threshold,
        wbt,
    )
    boundary_pts = xsections.loc[xsections["wallpoint"], "geom"]

    thresholds = determine_flood_extents(
        basin.subbasins, basin.hillslopes, boundary_pts
    )

    # apply flood thresholds
    flooded = apply_flood_thresholds(basin, thresholds)

    # return flooded raster
    pass


def apply_flood_thresholds(basin, thresholds):
    pass


def determine_flood_extents(
    boundary_pts,
    subbasins,
    hillslopes,
    min_points,
    default_threshold,
    percentile,
    buffer,
):
    results = []
    for reachID in finite_unique(subbasins):
        clipped_hillslopes = hillslopes.where(subbasins == reachID)

        for hillslopeID in finite_unique(clipped_hillslopes):
            points = boundary_pts.loc[boundary_pts["streamID"] == reachID]
            points = points.loc[points["hillslopeID"] == hillslopeID]

            if len(points) < min_points:
                threshold = default_threshold
            else:
                threshold = np.quantile(points["hand"], percentile)
                threshold = threshold + buffer
            results.append(
                {
                    "streamID": reachID,
                    "hillslopeID": hillslopeID,
                    "threshold": threshold,
                }
            )
    return pd.DataFrame(results)


def prep_data(basin, ta, sigma):
    smoothed_data = filter_nan_gaussian_conserving(basin.dem.data, sigma)
    smoothed = basin.dem.copy()
    smoothed.data = smoothed_data
    slope, curvature = ta.elevation_derivatives(smoothed)
    dataset = _make_dataset(basin)
    dataset["slope"] = slope
    dataset["curvature"] = curvature
    return dataset


def _make_dataset(basin):
    dataset = xr.Dataset()
    dataset["conditioned_dem"] = basin.conditioned_dem
    dataset["subbasin"] = basin.subbasins
    dataset["hillslope"] = basin.hillslopes
    dataset["hand"] = basin.hand
    dataset["slope"] = slope
    dataset["curvature"] = curvature
    dataset["flow_path"] = basin.flow_paths
    return dataset


def smooth_flowlines(flowlines, flowline_smooth_tolerance=3):
    smoothed = flowlines.apply(lambda x: x.simplify(flowline_smooth_tolerance))
    smoothed = smoothed.apply(lambda x: chaikin_smooth(taubin_smooth(x)))
    return smoothed


def climb_points(boundary_pts, dem, dataset, ta):
    inverted_dem = invert_dem(dem)
    fdir = ta.flow_dir(inverted_dem)
    p = finalize_wallpoints(boundary_pts, fdir)
    p = observe_values(
        p, dataset[["hand", "slope", "subbasin", "hillslope", "flow_path"]]
    )
    p["streamID"] = p["subbasin"]
    return p
