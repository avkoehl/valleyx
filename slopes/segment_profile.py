"""
Methods to segment a cross section profile into regions by finding breakpoints

These regions may be:
    - mean shift change point detection on slope using PELT
    - peaks of profile curvature
    - simplification of the elevation profile using Ramer-Douglas-Peucker algorithm

Then we apply a heuristic to classify these regions (find the breakpoint that is most likely valley wall)
in this step we may want to do some preprocessing, e.g. if elevation decreases stop the series

"""
import pandas as pd
import geopandas as gpd
import numpy as np
import ruptures as rpt
from scipy import signal
from rdp import rdp

import matplotlib.pyplot as plt

def segment_profiles(xsections: gpd.GeoDataFrame) -> gpd.GeoDataFrame: 
    """
    adds breakpoint column 
    """
    req = ["streamID", "xsID", "alpha", "slope", "dem", "curvature"]
    for col in req:
        if col not in xsections.columns:
            raise ValueError(f"Missing column: {col}, which is required")


    # preprocess each profile in the dataframe
    processed_dfs = []
    for (streamID, xsID), profile in xsections.groupby(['streamID', 'xsID']):

        peaks = signal.find_peaks(-profile['curvature'])[0]
        profile['bp'] = False
        profile.loc[profile.index[peaks], 'bp'] = True

        processed_dfs.append(profile)

    processed_df = gpd.GeoDataFrame(pd.concat(processed_dfs, ignore_index=True))
    return processed_df


def plot_segments(alpha_series, value_series, bps):
    fig, ax = plt.subplots()

    ax.scatter(alpha_series, value_series, marker='o')

    colors = ['white', 'lightblue']
    for i in range(len(bps) - 1):
            plt.axvspan(alpha_series.iloc[bps[i]], alpha_series.iloc[bps[i+1]],
                        facecolor=colors[i % 2], alpha=0.5)

    for bp in bps[1:-1]:
        plt.axvline(x=alpha_series.iloc[bp], linestyle='--', color='red',
                    linewidth=1)

    return fig, ax
