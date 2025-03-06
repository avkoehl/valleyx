import marimo

__generated_with = "0.11.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import os
    import shutil
    import toml

    os.environ["RUST_BACKTRACE"] = "full"

    from loguru import logger
    import rioxarray as rxr
    import geopandas as gpd

    from valleyx.flow.flow import flow_analysis
    from valleyx.reach.reach import delineate_reaches
    from valleyx.floor.floor import label_floors
    from valleyx.config import ValleyConfig
    from valleyx.wbt import setup_wbt
    from valleyx.terrain_analyzer import TerrainAnalyzer
    return (
        TerrainAnalyzer,
        ValleyConfig,
        delineate_reaches,
        flow_analysis,
        gpd,
        label_floors,
        logger,
        os,
        rxr,
        setup_wbt,
        shutil,
        toml,
    )


@app.cell
def _(
    TerrainAnalyzer,
    ValleyConfig,
    gpd,
    logger,
    os,
    rxr,
    setup_wbt,
    shutil,
    toml,
):
    logger.enable("valleyx")

    prefix = "1801010701"
    dem_file = "./data/test_sites_10m/1801010701-dem.tif"
    flowlines_file = "./data/test_sites_10m/1801010701-flowlines.shp"
    working_dir = "./working_dir/"
    params_file = "../ca-valley-floors/params/params_10m.toml"


    wbt = setup_wbt(working_dir, verbose=False, max_procs=1)
    dem = rxr.open_rasterio(dem_file, masked="True").squeeze()
    flowlines = gpd.read_file(flowlines_file)

    config = ValleyConfig.from_dict(toml.load(params_file))
    ta = TerrainAnalyzer(wbt, prefix=prefix)

    if os.path.exists(working_dir):
        shutil.rmtree(working_dir)

    os.makedirs(working_dir)
    return (
        config,
        dem,
        dem_file,
        flowlines,
        flowlines_file,
        params_file,
        prefix,
        ta,
        wbt,
        working_dir,
    )


@app.cell
def _(
    config,
    delineate_reaches,
    dem,
    flow_analysis,
    flowlines,
    label_floors,
    shutil,
    ta,
    working_dir,
):
    basin = flow_analysis(dem, flowlines, ta)
    basin = delineate_reaches(
        basin, ta, config.hand_threshold, config.spacing, config.minsize, config.window
    )
    floor = label_floors(
        basin,
        ta,
        config.max_floor_slope,
        config.foundation_slope,
        config.sigma,
        config.line_spacing,
        config.line_width,
        config.line_max_width,
        config.point_spacing,
        config.min_hand_jump,
        config.ratio,
        config.min_peak_prominence,
        config.min_distance,
        config.num_cells,
        config.slope_threshold,
        config.buffer,
        config.min_points,
        config.percentile,
        config.default_threshold,
    )


    shutil.rmtree(working_dir)
    return basin, floor


@app.cell
def _(floor):
    floor.plot()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
