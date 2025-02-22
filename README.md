# Valleyx

`valleyx` is a python package for extracting valley floors from digital elevation models.

Combines two approaches:
1. low slope areas connected to the flowlines
2. elevation above stream thresholding 

![map of extracted valley floor](/img/result.png)

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
import geopandas as gpd
import rioxarray as rxr

from valleyx import ValleyConfig
from valleyx import extract_valleys
from valleyx.wbt import setup_wbt

dem = rxr.open_rasterio(dem_file_path, masked=True).squeeze()
flowlines = gpd.read_file(flowlines_file_path)

dem, flowlines = load_input(dem_file_path, flowlines_file_path)
wbt = setup_wbt(working_directory_path, verbose=False, max_procs=1) 
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
    max_floor_slope=14,
    default_threshold=5,
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

## Contact

Arthur Koehl  
avkoehl at ucdavis .edu
