import argparse
import os

import rioxarray as rxr
import geopandas as gpd
from shapelysmooth import chaikin_smooth
from shapelysmooth import taubin_smooth
import xarray as xr
import whitebox
import toml

from slopes.terrain.subbasins import label_subbasins
from slopes.terrain.hillslopes import label_hillslopes
from slopes.profile.network_xsections import network_xsections
from slopes.utils import observe_values
from slopes.profile.preprocess_profile import preprocess_profiles
from slopes.profile.classify_profile import classify_profiles
from slopes.reach.reaches import delineate_reaches
from slopes.floor.floor import label_floors
from slopes.max_ascent.classify_profile_max_ascent import classify_profiles_max_ascent
from slopes.terrain.flow_acc import flow_accumulation_workflow
from slopes.terrain.align_flowlines import align_flowlines
from slopes.terrain.surface import elev_derivatives
from slopes.terrain.hand import channel_relief


def setup_wbt(working_dir, verbose=False):
    wbt = whitebox.WhiteboxTools()
    wbt.set_working_dir(os.path.abspath(os.path.expanduser(working_dir)))
    wbt.verbose = verbose
    return wbt


def load_input(dem_path, flowline_path):
    dem = rxr.open_rasterio(dem_path, masked=True).squeeze()
    flowlines = gpd.read_file(flowline_path)
    if flowlines.crs is None:
        flowlines.crs = dem.rio.crs
    return dem, flowlines


def process_topography(dem, flowlines, wbt, sigma):
    conditioned, flow_dir, flow_acc = flow_accumulation_workflow(dem, wbt)
    aligned_flowlines, flowpaths = align_flowlines(flowlines, flow_acc, flow_dir, wbt)
    smoothed, slope, curvature = elev_derivatives(conditioned, wbt, sigma)
    hand = channel_relief(conditioned, flowpaths, wbt, method="d8")

    dataset = xr.Dataset()
    dataset["conditioned_dem"] = conditioned
    dataset["flow_dir"] = flow_dir
    dataset["flow_acc"] = flow_acc
    dataset["flow_path"] = flowpaths
    dataset["hand"] = hand
    dataset["dem"] = smoothed
    dataset["slope"] = slope
    dataset["curvature"] = curvature

    dataset["subbasin"] = label_subbasins(
        dataset["flow_dir"], dataset["flow_acc"], dataset["flow_path"], wbt
    )
    dataset["hillslope"] = label_hillslopes(
        dataset["flow_path"], dataset["flow_dir"], dataset["subbasin"], wbt
    )
    return dataset, aligned_flowlines


def smooth_flowlines(flowlines):
    smoothed = flowlines.apply(lambda x: x.simplify(3))
    smoothed = smoothed.apply(lambda x: chaikin_smooth(taubin_smooth(x)))
    return smoothed


def compute_profiles(
    flowlines,
    dataset,
    line_spacing,
    line_width,
    point_spacing,
    subbasins,
    min_hand_jump,
    ratio,
    min_distance,
):
    xsections = network_xsections(
        flowlines, line_spacing, line_width, point_spacing, subbasins
    )
    profiles = observe_values(xsections, dataset)
    processed = preprocess_profiles(profiles, min_hand_jump, ratio, min_distance)
    return processed


def wall_points_max_ascent(profiles, num_cells, dem, slope, slope_threshold, wbt):
    classified = classify_profiles_max_ascent(
        profiles, dem, slope, num_cells, slope_threshold, wbt
    )
    wall_points = classified.loc[classified["wallpoints"]]
    return wall_points


def wall_points_curv(profiles, slope_threshold, distance, height):
    classified = classify_profiles(profiles, slope_threshold, distance, height)
    wall_points = classified.loc[classified["wallpoints"]]
    return wall_points


def main(
    wbt,
    dem,
    flowlines,
    num_points=200,
    sigma = 3,
    spacing=30,
    minsize= 200,
    window = 4,
    line_spacing=3,
    line_width=100,
    point_spacing=1,
    min_hand_jump=15,
    ratio=2.5,
    min_distance=10,
    num_cells=5,
    slope_threshold=12,
    distance=3,
    height=0.02,
    hillslope_threshold=15,
    plains_threshold=4,
    buffer=1,
    min_points=15,
    quantile=0.90,
):


    dataset, aligned_flowlines = process_topography(dem, flowlines, wbt, sigma)
    dataset, flowlines_reaches = delineate_reaches(
        dataset, aligned_flowlines, wbt, num_points, spacing, minsize, window
    )
    flowlines = smooth_flowlines(flowlines_reaches)

    profiles = compute_profiles(
        flowlines,
        dataset,
        line_spacing,
        line_width,
        point_spacing,
        dataset["subbasins"],
        min_hand_jump,
        ratio,
        min_distance,
    )

    wp_ma = wall_points_max_ascent(
        profiles, num_cells, dataset['dem'], dataset['slope'], slope_threshold, wbt
    )
    wp_curv = wall_points_curv(
        profiles, slope_threshold, distance, height
    )

    floors_ma = label_floors(
        wp_ma,
        dataset,
        hillslope_threshold,
        plains_threshold,
        buffer,
        min_points,
        quantile,
    )
    floors_curv = label_floors(
        wp_curv,
        dataset,
        hillslope_threshold,
        plains_threshold,
        buffer,
        min_points,
        quantile,
    )
    return floors_ma, floors_curv


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dem_file", type=str, required=True)
    parser.add_argument("--flowline_file", type=str, required=True)
    parser.add_argument("--working_dir", type=str, required=True)
    parser.add_argument("--param_file", type=str, required=True)
    parser.add_argument("--odir", type=str, required=True)
    args = parser.parse_args()

    wbt = setup_wbt(args.working_dir)
    dem, flowlines = load_input(args.dem_file, args.flowlines_file)

    params = toml.load(args.param_file)
    floors_ma, floors_curv = main(wbt, dem, flowlines, **params)

    # make odir if doesn't exist
    os.makedirs(args.odir, exist_ok=True)

    #  save floors_ma and floors_curv to odir
    floors_ma.rio.to_raster(os.path.join(args.odir, "floors_ma.tif"))
    floors_curv.rio.to_raster(os.path.join(args.odir, "floors_curv.tif"))
