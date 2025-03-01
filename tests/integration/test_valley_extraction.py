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
from valleyx.wbt import setup_wbt

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
    return ValleyConfig(
        hand_threshold=10.0,
        spacing=50,
        minsize=300,
        window=5,
        max_floor_slope=15,
        foundation_slope=5,
        sigma=4,
        line_spacing=50,
        line_width=500,
        line_max_width=500,
        point_spacing=10,
        min_hand_jump=15,
        ratio=3.5,
        min_peak_prominence=20,
        min_distance=30,
        num_cells=5,
        slope_threshold=10,
        buffer=1,
        min_points=10,
        percentile=0.80,
        default_threshold=5,
    )


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
        basin.flowlines.to_file(output_dir / "test_flowlines_output.shp")

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
