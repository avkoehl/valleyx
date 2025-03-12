# tests/integration/test_valley_extraction.py

import os
import shutil
import tempfile
from pathlib import Path

import geopandas as gpd
import pytest
import rioxarray as rxr

from valleyx.config import ValleyConfig
from valleyx.core import flow_analysis, delineate_reaches, label_floors
from valleyx.terrain_analyzer import TerrainAnalyzer
from valleyx.core import setup_wbt

# Get the tests directory path
TESTS_DIR = Path(__file__).parent.parent
DATA_DIR = TESTS_DIR / "data"


@pytest.fixture
def test_data():
    """Load sample test data"""
    # Load DEM
    dem_path = DATA_DIR / "180701020604-dem.tif"
    dem = rxr.open_rasterio(dem_path, masked=True).squeeze()

    # Load flowlines
    flowlines_path = DATA_DIR / "180701020604-flowlines.shp"
    flowlines = gpd.read_file(flowlines_path).geometry

    return dem, flowlines


@pytest.fixture
def working_dir():
    """Create and cleanup a temporary working directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def config():
    """Create test configuration"""
    cfg = ValleyConfig()
    return cfg


def test_valley_extraction_workflow(test_data, working_dir, config):
    """Test the complete valley extraction workflow"""
    dem, flowlines = test_data

    # Initialize WhiteboxTools
    wbt = setup_wbt(working_dir, verbose=False, max_procs=1)

    # Initialize TerrainAnalyzer
    ta = TerrainAnalyzer(wbt, prefix="test")

    # Run extraction
    basin = flow_analysis(dem, flowlines, ta)

    basin = delineate_reaches(
        basin,
        ta,
        config.reach.hand_threshold,
        config.reach.spacing,
        config.reach.minsize,
        config.reach.window,
    )

    floor, _, _ = label_floors(
        basin,
        ta,
        config.floor.max_floor_slope,
        config.floor.max_fill_area,
        config.floor.foundation.slope,
        config.floor.foundation.sigma,
        config.floor.flood.xs_spacing,
        config.floor.flood.xs_max_width,
        config.floor.flood.point_spacing,
        config.floor.flood.min_hand_jump,
        config.floor.flood.ratio,
        config.floor.flood.min_peak_prominence,
        config.floor.flood.min_distance,
        config.floor.flood.num_cells,
        config.floor.flood.slope_threshold,
        config.floor.flood.min_points,
        config.floor.flood.percentile,
        config.floor.flood.buffer,
        config.floor.flood.default_threshold,
    )

    # Validation
    assert (floor > 0).any(), "No valley areas were identified"

    # cleanup working directory
    shutil.rmtree(working_dir)

    # Optional: Save outputs for visual inspection during development
    debug = True
    if debug:
        output_dir = TESTS_DIR / "outputs"

        # if output directory exits, remove it
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)

        floor.rio.to_raster(output_dir / "test_floor_output.tif")
        basin.flowlines.to_file(
            output_dir / "test_flowlines_output.gpkg", driver="GPKG"
        )

        visualize_results(dem, floor, basin.flowlines, output_dir)


# Optional: Add a function to help visualize results during development
# TODO:
def visualize_results(dem, floor, flowlines, output_dir=None):
    """Helper function to visualize results for debugging"""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 10))
    dem.plot(ax=ax, cmap="terrain")
    floor.plot(ax=ax, cmap="viridis")
    flowlines.plot(ax=ax, color="blue")

    if output_dir:
        plt.savefig(output_dir / "valley_extraction.png", dpi=300)
    else:
        plt.show()
