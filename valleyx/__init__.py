"""
ValleyX: A Python package for valley floor extraction and analysis

This package provides tools for analyzing digital elevation models (DEMs) to
identify valley floors through a multi-step process including flow analysis,
reach delineation, wall point detection, and floor labeling.

Main Components
--------------
- Flow Analysis: Hydrological analysis and stream network processing
- Reach Delineation: Segmentation of stream networks into reaches
- Wall Detection: Identification of valley wall points
- Floor Labeling: Classification of valley floor areas

Example
-------
>>> import valleyx
>>> from valleyx import ValleyConfig
>>> config = ValleyConfig(
...     hand_threshold=5.0,
...     spacing=30,
...     minsize=100,
...     window=5,
...     sigma=1.0,
...     line_spacing=50,
...     line_width=200,
...     line_max_width=1000,
...     point_spacing=10,
...     min_hand_jump=2,
...     ratio=0.5,
...     min_peak_prominence=2,
...     min_distance=5,
...     num_cells=10,
...     slope_threshold=0.1,
...     foundation_slope=0.05,
...     buffer=2.0,
...     min_points=5,
...     percentile=0.9
... )
>>> results = valleyx.extract_valleys(dem, flowlines, wbt, config)
"""

__version__ = "1.0.0"

from .core import (
    extract_valleys,
    ValleyConfig,
)

from .flow_analysis import flow_analysis
from .reach_delineation import delineate_reaches
from .wall_detection import detect_wallpoints
from .label_floors import (
    label_floors,
    subbasin_floors,
)

from .utils import (
    setup_wbt,
    load_input,
    make_dir,
    translate_to_wbt,
)

# Define the public API
__all__ = [
    # Core functionality
    "extract_valleys",
    "ValleyConfig",
    # Main processing steps
    "flow_analysis",
    "delineate_reaches",
    "detect_wallpoints",
    "label_floors",
    "subbasin_floors",
    # Utility functions
    "setup_wbt",
    "load_input",
    "make_dir",
    "translate_to_wbt",
]

# Package metadata
__author__ = "Arthur Koehl"
__email__ = "avkoehl@ucdavis.edu"
__description__ = "A Python package for valley floor extraction and analysis"
__url__ = "https://github.com/avkoehl/valleyx"
