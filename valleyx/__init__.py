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

from .wbt import setup_wbt
from .terrain_analyzer import TerrainAnalyzer
from .basin import BasinData
from .flow.flow import flow_analysis
from .reach.reach import delineate_reaches
from .floor.floor import label_floors

__all__ = [
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

__version__ = "2.0.0"
