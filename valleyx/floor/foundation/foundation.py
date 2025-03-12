"""
Finds all the low slope areas connected to the flowpath network

- smooth
- segment into super pixels
- threshold super pixel regions by slope
- run connectivity algorithm
"""

import numpy as np
from scipy.ndimage import binary_closing
from skimage.morphology import isotropic_dilation

from valleyx.floor.foundation.connect import connected


def foundation(slope, flowpaths, apst):
    thresholded = slope < apst

    fp = flowpaths > 0
    dilated = isotropic_dilation(fp, radius=5)
    fp.data = dilated

    foundation = connected(thresholded, fp)
    foundation.data[flowpaths > 0] = True

    structure = np.ones((5, 5))
    foundation.data = binary_closing(foundation.data, structure=structure, iterations=3)

    return foundation
