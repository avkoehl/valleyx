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
    names = [
        "temp",
        "conditioned_dem",
        "flow_dir",
        "flow_acc",
    ]
    fnames = [os.path.join(work_dir, f"{wbt.instance_id}-{name}.tif") for name in names]
    files = {name: file for name, file in zip(names, fnames)}

    dem.rio.to_raster(files["temp"])
    try:
        wbt.fill_depressions(
            files["temp"],
            files["conditioned_dem"],
            fix_flats=True,
            flat_increment=None,
            max_depth=None,
        )

        wbt.d8_pointer(
            files["conditioned_dem"],
            files["flow_dir"],
            esri_pntr=False,
        )

        wbt.d8_flow_accumulation(
            files["flow_dir"],
            files["flow_acc"],
            out_type="cells",
            log=False,
            clip=False,
            pntr=True,
            esri_pntr=False,
        )

    except Exception as e:
        for file in fnames:
            if os.path.exists(file):
                os.remove(file)
        raise RuntimeError(f"Unexpected error in flow accumulation workflow: {e}")

    # load the files
    with rxr.open_rasterio(files["conditioned_dem"], masked=True) as src:
        conditioned = src.squeeze().load()
    with rxr.open_rasterio(files["flow_dir"], masked=True) as src:
        flow_dir = src.squeeze().load()
    with rxr.open_rasterio(files["flow_acc"], masked=True) as src:
        flow_acc = src.squeeze().load()

    for file in fnames:
        if os.path.exists(file):
            os.remove(file)

    return conditioned, flow_dir, flow_acc
