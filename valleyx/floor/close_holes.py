# fill holes in a binary image that are smaller than a given size

import numpy as np
from skimage.measure import label


def close_holes(binary_image, max_hole_size):
    labeled_image, num_components = label(binary_image)
    for i in range(1, num_components + 1):
        if np.sum(labeled_image == i) < max_hole_size:
            binary_image[labeled_image == i] = 1
    return binary_image
