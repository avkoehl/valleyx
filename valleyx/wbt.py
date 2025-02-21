import os
import uuid

import whitebox


class CustomWhiteboxTools(whitebox.WhiteboxTools):
    """
    Extends the WhiteboxTools class that contains a unique identifier for the
    instance. This is useful for running multiple instances of WhiteBoxTools
    concurrently so that the output files do not conflict.

    In methods that write to disk, the output file path is modified to include
    the unique identifier. Can add custom prefix, e.g. '18050502'
    """

    def __init__(self, prefix: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uuid = str(uuid.uuid4())
        if prefix:
            prefix = str(prefix)
            clean_prefix = "".join(c for c in prefix if c.isalnum() or c in "_-")
            self.instance_id = f"{clean_prefix}_{self.uuid}"
        else:
            self.instance_id = self.uuid


def setup_wbt(working_dir, verbose, max_procs, prefix=None):
    wbt = CustomWhiteboxTools(prefix=prefix)

    working_dir = os.path.abspath(os.path.expanduser(working_dir))
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)
    wbt.set_working_dir(working_dir)

    wbt.set_verbose_mode(verbose)  # default True
    wbt.set_max_procs(max_procs)  # default -1
    return wbt
