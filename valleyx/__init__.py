# valleyx/__init__.py
"""
ValleyX: Valley floor extraction and analysis

This package provides tools for hydrologic terrain analysis
and valley floor delineation.

Main Functions
-------------
flow_analysis : Run flow analysis, subbasin delineation and elevation above stream
delineate_reaches : Delineate stream reaches based on valley bottom width
label_floors : Map valley floor

"""

from .terrain_analyzer import TerrainAnalyzer
from .basin import BasinData
from .config import ValleyConfig
from .config import ReachConfig
from .config import FloorConfig
from .config import FloodConfig
from .config import FoundationConfig
from .flow.flow import flow_analysis
from .reach.reach import delineate_reaches
from .floor.floor import label_floors
from .core import extract_valleys
from .core import setup_wbt

__all__ = [
    # main
    "extract_valleys",
    # Configuration
    "ValleyConfig",
    "ReachConfig",
    "FloorConfig",
    "FloodConfig",
    "FoundationConfig",
    # Core data structure
    "BasinData",
    # Main analytical functions
    "flow_analysis",
    "delineate_reaches",
    "label_floors",
    # Setup utilities
    "setup_wbt",
    "TerrainAnalyzer",
]

__version__ = "2.1.0"
