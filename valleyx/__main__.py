import argparse
import os
import shutil
import sys
import toml

import geopandas as gpd
from loguru import logger
import rioxarray as rxr

from valleyx.core import extract_valleys
from valleyx.core import ValleyConfig
from valleyx.wbt import setup_wbt


def setup_logging(enable_logging, log_file):
    if enable_logging:
        logger.enable("valleyx")
        if log_file:
            logger.remove()

            logger.add(log_file, level="DEBUG")
        else:
            logger.remove()
            logger.add(sys.stderr, level="DEBUG")
        logger.info("logging enabled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dem_file", type=str, required=True)
    parser.add_argument("--flowlines_file", type=str, required=True)
    parser.add_argument("--working_dir", type=str, required=True)
    parser.add_argument("--param_file", type=str, required=True)
    parser.add_argument("--floor_ofile", type=str, required=True)
    parser.add_argument("--enable_logging", action="store_true")  # false if not set
    parser.add_argument("--log_file", type=str, default=None)
    args = parser.parse_args()

    setup_logging(args.enable_logging, args.log_file)

    wbt = setup_wbt(args.working_dir, verbose=False, max_procs=1)
    dem = rxr.open_rasterio(args.dem_file, masked=True).squeeze()
    flowlines = gpd.read_file(args.flowlines_file)
    params = toml.load(args.param_file)

    config = ValleyConfig.from_dict(params)

    if os.path.exists(args.working_dir):
        shutil.rmtree(args.working_dir)
    os.makedirs(args.working_dir)

    results = extract_valleys(dem, flowlines, wbt, config)

    results.rio.to_raster(args.floor_ofile)

    shutil.rmtree(args.working_dir)
