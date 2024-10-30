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
    work_dir = wbt.work_dir
    names = ["temp", "conditioned_dem", "flow_dir", "flow_acc"]
    fnames = [os.path.join(work_dir, name + '.tif') for name in names]
    files = {name:file for name,file in zip(names,fnames)}

    dem.rio.to_raster(files['temp'])

    wbt.fill_depressions(
            files['temp'],
            files['conditioned_dem'],
            fix_flats = True,
            flat_increment = None,
            max_depth = None)

    wbt.d8_pointer(
            files['conditioned_dem'], 
            files['flow_dir'], 
            esri_pntr=False, 
            )

    wbt.d8_flow_accumulation(
            files['conditioned_dem'], 
            files['flow_acc'], 
            out_type="cells", 
            log=False, 
            clip=False, 
            pntr=False, 
            esri_pntr=False, 
            )

    # load the files
    conditioned = rxr.open_rasterio(files['conditioned_dem'], masked=True).squeeze()
    flow_dir = rxr.open_rasterio(files['flow_dir'], masked=True).squeeze()
    flow_acc = rxr.open_rasterio(files['flow_acc'], masked=True).squeeze()

    # remove any file that was created
    os.remove(files['temp'])

    return conditioned, flow_dir, flow_acc
