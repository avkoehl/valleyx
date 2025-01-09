# Valleyx

This is the code for 'valleyx', a python package for extracting valley floors from digital elevation models.

## Installation

### Prerequisites

- Python 3.10 or higher
- [Poetry (package manager)](https://python-poetry.org/)

### Installing from Github

1. Clone the repository
```bash
git clone git@github.com:avkoehl/valleyx.git
cd valleyx
```

2. Install dependencies using Poetry
```bash
poetry install
```

Optionally install with additional development dependencies including matplotlib and jupyter
```bash
poetry install --with dev
```

## Usage

### As a python package

Import and use the modules in your python code:

```python
from valleyx import ValleyConfig
from valleyx import extract_valleys
from valleyx.utils import setup_wbt
from valleyx.utils import load_input

dem, flowlines = load_input(dem_file_path, flowlines_file_path)
wbt = setup_wbt(working_directory_path) # make sure directory exists
config = ValleyConfig(
    # Reach delineation params
    hand_threshold=10,
    spacing=20,
    minsize=300,
    window=5,
    # Dem smoothing
    sigma=1.5,
    # Cross Section Params
    line_spacing=30,
    line_width=600,
    line_max_width=600,
    point_spacing=10,
    # Cross section preprocessing
    min_hand_jump=15,
    ratio=2.5,
    min_distance=20,
    min_peak_prominence=10,
    # Sustained slope params
    num_cells=8,
    slope_threshold=10,
    # Floor labeling params
    foundation_slope=5,
    buffer=1,
    min_points=15,
    percentile=0.80,
    max_floor_slope=14
)

results = extract_valleys(dem, flowlines, wbt, config)
```

### Command Line Interface

```bash
# Using poetry
poetry run python -m valleyx -h
```

```bash
# if installed in your environment
python -m valleyx -h
```

## File Structure

./
    __init__.py - Package initialization
    __main__.py - Entry point of the package
    core.py - Core functionality
    flow_analysis.py - Flow analysis logic
    label_floors.py - Floor labeling and classification
    reach_delineation.py - River reach segmentation logic
    utils.py - Shared utility functions
    wall_detection.py - Wall point detection logic

    floor/
        connect.py - Floor connectivity analysis
        foundation.py - Base floor processing

    geometry/
        centerline.py - Centerline extraction algorithm
        cross_section.py - Cross-sectional analysis tools
        geom_utils.py - Shapely utility functions
        width.py - Width calculation methods on polygons

    max_ascent/
        classify_profile_max_ascent.py - Profile classification based on maximum ascent
        max_ascent.py - Maximum ascent calculation algorithms

    profile/
        classify_profile.py - General profile classification
        convert_wp.py - Post Processing for detected wall points
        network_xsections.py - Network cross-section analysis
        preprocess_profile.py - Profile preprocessing functions
        split.py - Profile splitting utilities

    raster/
        raster_utils.py - Raster processing utilities
        vectorize.py - Raster to vector conversion

    reach/
        reach.py - Reach analysis core functionality
        rough_out.py - Initial reach estimation

    terrain/
        align_flowlines.py - Flowline alignment with terrain
        cost.py - Cost surface calculations
        flow_acc.py - Flow accumulation algorithms
        flow_dir.py - Flow direction analysis
        hand.py - Height Above Nearest Drainage calculations
        hillslopes.py - Hillslope delineation
        subbasins.py - Sub-basin delineation
        surface.py - Surface analysis utilities

## Contact

Arthur Koehl
avkoehl at ucdavis .edu
