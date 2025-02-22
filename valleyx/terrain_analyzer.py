import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import rioxarray as rxr


class TerrainAnalyzer:
    def __init__(self, wbt, prefix):
        self.wbt = wbt
        self.prefix = prefix

    # helper
    @staticmethod
    def load_raster(path):
        return rxr.open_rasterio(path, masked=True).squeeze()

    @staticmethod
    def cleanup_files(files):
        for file in files.values():
            if os.path.exists(file):
                if file.endswith(".shp"):
                    for ext in [".dbf", ".prj", ".shx", ".cpg"]:
                        associated_file = file.replace(".shp", ext)
                        if os.path.exists(associated_file):
                            os.remove(associated_file)
                os.remove(file)

    def construct_fname(self, name, ext):
        base = Path(self.wbt.work_dir)
        full = base / f"{self.prefix}-{name}.{ext}"
        return str(full.absolute())

    def create_temp_raster_paths(self, names):
        return {name: self.construct_fname(name, "tif") for name in names}

    def create_temp_vector_paths(self, names):
        return {name: self.construct_fname(name, "shp") for name in names}

    def flow_acc_workflow(self, dem):
        manifest = self.create_temp_raster_paths(
            ["dem", "cdem", "flow_dir", "flow_acc"]
        )
        dem.rio.to_raster(manifest["dem"])
        try:
            self.wbt.fill_depressions(
                manifest["dem"],
                manifest["cdem"],
                fix_flats=True,
                flat_increment=None,
                max_depth=None,
            )

            self.wbt.d8_pointer(
                manifest["cdem"],
                manifest["flow_dir"],
                esri_pntr=False,
            )

            self.wbt.d8_flow_accumulation(
                manifest["flow_dir"],
                manifest["flow_acc"],
                out_type="cells",
                log=False,
                clip=False,
                pntr=True,
                esri_pntr=False,
            )
            cdem = TerrainAnalyzer.load_raster(manifest["cdem"])
            fdir = TerrainAnalyzer.load_raster(manifest["flow_dir"])
            acc = TerrainAnalyzer.load_raster(manifest["flow_acc"])

        except Exception as e:
            raise ValueError(f"Error in flow accumulation workflow: {e}") from e
        finally:
            TerrainAnalyzer.cleanup_files(manifest)

        return cdem, fdir, acc

    def subbasins(self, flow_dir, pour_points):
        rasters = self.create_temp_raster_paths(["flow_dir", "subbasins"])
        vectors = self.create_temp_vector_paths(["pour_points"])
        manifest = {**rasters, **vectors}

        flow_dir.rio.to_raster(manifest["flow_dir"])
        pour_points.to_file(manifest["pour_points"])

        try:
            self.wbt.watershed(
                manifest["flow_dir"], manifest["pour_points"], manifest["subbasins"]
            )
            subbasins = TerrainAnalyzer.load_raster(manifest["subbasins"])

        except Exception as e:
            raise ValueError(f"Error in subbasin workflow: {e}") from e

        finally:
            TerrainAnalyzer.cleanup_files(manifest)

        # need to relabel the subbasins to match the pour points
        # in wbt subbasin id is incremented from 1
        streamIDSs = pour_points.index
        ind = 1
        mapping = {}
        for streamID in streamIDSs:
            mapping[ind + 0.5] = streamID
            ind += 1

        subbasins = subbasins + 0.5
        for key, value in mapping.items():
            subbasins.data[subbasins.data == key] = value

        subbasins = subbasins.rio.write_nodata(np.nan)
        subbasins = subbasins.astype(np.float32)
        return subbasins

    def hillslopes(self, flow_dir, flow_paths):
        manifest = self.create_temp_raster_paths(
            ["flow_dir", "flow_paths", "hillslopes"]
        )
        flow_dir.rio.to_raster(manifest["flow_dir"])
        flow_paths.rio.to_raster(manifest["flow_paths"])

        try:
            self.wbt.hillslopes(
                manifest["flow_dir"], manifest["flow_paths"], manifest["hillslopes"]
            )
            hillslopes = TerrainAnalyzer.load_raster(manifest["hillslopes"])
        except Exception as e:
            raise ValueError(f"Error in hillslope workflow: {e}") from e
        finally:
            TerrainAnalyzer.cleanup_files(manifest)
        return hillslopes

    def hand(self, dem, flow_paths):
        manifest = self.create_temp_raster_paths(["dem", "flow_paths", "hand"])
        dem.rio.to_raster(manifest["dem"])
        flow_paths.rio.to_raster(manifest["flow_paths"])

        try:
            self.wbt.elevation_above_stream(
                manifest["dem"], manifest["flow_paths"], manifest["hand"]
            )
            hand = TerrainAnalyzer.load_raster(manifest["hand"])
        except Exception as e:
            raise ValueError(f"Error in hand workflow: {e}") from e
        finally:
            TerrainAnalyzer.cleanup_files(manifest)
        return hand

    def elevation_derivatives(self, dem):
        manifest = self.create_temp_raster_paths(["dem", "slope", "profile_curvature"])
        dem.rio.to_raster(manifest["dem"])

        try:
            self.wbt.slope(manifest["dem"], manifest["slope"], units="degrees")
            self.wbt.profile_curvature(manifest["dem"], manifest["profile_curvature"])

            slope = TerrainAnalyzer.load_raster(manifest["slope"])
            curvature = TerrainAnalyzer.load_raster(manifest["profile_curvature"])
        except Exception as e:
            raise ValueError(f"Error in elevation derivative workflow: {e}") from e
        finally:
            TerrainAnalyzer.cleanup_files(manifest)
        return slope, curvature

    def flowpaths_to_flowlines(self, flow_paths, flow_dir):
        rasters = self.create_temp_raster_paths(["flowpaths", "flowdir"])
        vectors = self.create_temp_vector_paths(["flowlines"])
        manifest = {**rasters, **vectors}

        flow_paths.rio.to_raster(manifest["flowpaths"])
        flow_dir.rio.to_raster(manifest["flowdir"])

        try:
            self.wbt.raster_streams_to_vector(
                manifest["flowpaths"], manifest["flowdir"], manifest["flowlines"]
            )
            flowlines = gpd.read_file(manifest["flowlines"])
        except Exception as e:
            raise ValueError(f"Error in flowpaths to flowlines workflow: {e}") from e
        finally:
            TerrainAnalyzer.cleanup_files(manifest)
        return flowlines

    def trace_flowpaths(self, flow_dir, flow_acc, channel_heads, snap_dist):
        rasters = self.create_temp_raster_paths(
            ["flow_dir", "flow_acc", "flow_paths", "flow_paths_id"]
        )
        vectors = self.create_temp_vector_paths(
            ["channel_heads", "snapped_channel_heads", "flowlines"]
        )
        manifest = {**rasters, **vectors}

        flow_acc.rio.to_raster(manifest["flow_acc"])
        flow_dir.rio.to_raster(manifest["flow_dir"])
        channel_heads.to_file(manifest["channel_heads"])

        try:
            self.wbt.snap_pour_points(
                manifest["channel_heads"],
                manifest["flow_acc"],
                manifest["snapped_channel_heads"],
                snap_dist=snap_dist,
            )
            self.wbt.trace_downslope_flowpaths(
                manifest["snapped_channel_heads"],
                manifest["flow_dir"],
                manifest["flow_paths"],
            )
            self.wbt.stream_link_identifier(
                manifest["flow_dir"], manifest["flow_paths"], manifest["flow_paths_id"]
            )
            self.wbt.raster_streams_to_vector(
                manifest["flow_paths_id"], manifest["flow_dir"], manifest["flowlines"]
            )

            flowlines = gpd.read_file(manifest["flowlines"])
            flow_paths = TerrainAnalyzer.load_raster(manifest["flow_paths_id"])
        except Exception as e:
            raise ValueError(f"Error in trace flowpaths workflow: {e}") from e
        finally:
            TerrainAnalyzer.cleanup_files(manifest)
        return flowlines, flow_paths
