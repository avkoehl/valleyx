import os

import rioxarray as rxr

def flow_accumulation_workflow(dem, wbt):
    """
    input:
        dem
        wbt

    output:
        conditioned_dem
        flow_dir
        flow_acc
    """
    wbt_messages = []
    verbose_flipped = False
    if not wbt.verbose:
        verbose_flipped = True
        wbt.set_verbose_mode(True) # temporary
    def my_callback(value):
        if not '%' in value:
            wbt_messages.append(value)

    work_dir = wbt.work_dir
    names = ["temp", "conditioned_dem", "flow_dir", "flow_acc"]
    fnames = [os.path.join(work_dir, name + '.tif') for name in names]
    files = {name:file for name,file in zip(names,fnames)}

    created_files = []
    try:
        dem.rio.to_raster(files['temp'])

        wbt.fill_depressions(
                files['temp'],
                files['conditioned_dem'],
                fix_flats = True,
                flat_increment = None,
                max_depth = None,
                callback=my_callback)

        wbt.d8_pointer(
                files['conditioned_dem'], 
                files['flow_dir'], 
                esri_pntr=False, 
                callback=my_callback
                )

        wbt.d8_flow_accumulation(
                files['flow_dir'], 
                files['flow_acc'], 
                out_type="cells", 
                log=False, 
                clip=False, 
                pntr=True, 
                esri_pntr=False, 
                callback=my_callback
                )

        # load the files
        with rxr.open_rasterio(files['conditioned_dem'], masked=True) as src:
            conditioned = src.squeeze()
        with rxr.open_rasterio(files['flow_dir'], masked=True) as src:
            flow_dir = src.squeeze()
        with rxr.open_rasterio(files['flow_acc'], masked=True) as src:
            flow_acc = src.squeeze()

        return conditioned, flow_dir, flow_acc

    except (IOError, OSError) as e:
        raise RuntimeError(f"File operation failed: {e}\nwhitebox messages: {' '.join(wbt_messages)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during DEM processing: {e}\nwhitebox messages: {' '.join(wbt_messages)}")

    finally:
        for file in created_files:
            if os.path.exists(file):
                os.remove(file)
        if verbose_flipped:
            wbt.set_verbose_mode(False)
