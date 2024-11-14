import argparse
import os
import toml
import shutil
from loguru import logger

from valleyx.core import extract_valleys
from valleyx.core import ValleyConfig
from valleyx.utils import setup_wbt
from valleyx.utils import make_dir
from valleyx.utils import load_input

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
    parser.add_argument("--flowlines_ofile", type=str, default=None)
    parser.add_argument("--wp_ofile", type=str, default=None)
    parser.add_argument("--enable_logging", action='store_true') # false if not set
    parser.add_argument("--log_file", type=str, default=None)
    args = parser.parse_args()

    setup_logging(args.enable_logging, args.log_file)

    wbt = setup_wbt(args.working_dir)
    dem, flowlines = load_input(args.dem_file, args.flowlines_file)
    params = toml.load(args.param_file)

    config = ValleyConfig.from_dict(params)

    make_dir(args.working_dir, remove_existing=True)

    results = extract_valleys(
            dem,
            flowlines,
            wbt,
            config
    )

    results['floor'].rio.to_raster(args.floor_ofile)

    if args.flowlines_ofile:
        results['flowlines'].to_file(args.flowlines_ofile)

    if args.wp_ofile:
        results['wallpoints'].to_file(args.wp_ofile)

    shutil.rmtree(args.working_dir)
