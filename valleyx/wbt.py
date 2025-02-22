import os

import whitebox


def setup_wbt(working_dir, verbose, max_procs):
    wbt = whitebox.WhiteboxTools()

    working_dir = os.path.abspath(os.path.expanduser(working_dir))
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)
    wbt.set_working_dir(working_dir)

    wbt.set_verbose_mode(verbose)  # default True
    wbt.set_max_procs(max_procs)  # default -1
    return wbt
