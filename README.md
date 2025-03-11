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

Optionally install with additional development dependencies including
matplotlib and jupyter
```bash
poetry install --with dev
```

## Usage

### Basic Usage
Import and use the modules in your python code:

```python
import rioxarray as rxr
import geopandas as gpd

from valleyx import ValleyConfig
from valleyx import extract_valleys

dem = rxr.open_rasterio('path/to/dem.tif')
flowlines = gpd.read_file('path/to/flowlines.shp')
config = ValleyConfig()

floors, flowlines = extract_valleys(dem, flowlines, config)
```

### Configuration Options

To customize parameters, create a `ValleyConfig` object and modify the
parameters:

```python
config = ValleyConfig()
config.reach.hand_threshold = 5
```

For more information on the parameters:
```python
help(ValleyConfig)
```


## Contact

Arthur Koehl  
avkoehl at ucdavis .edu
