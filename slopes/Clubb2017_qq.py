import matplotlib.pyplot as plt
import scipy.stats as stats
import numpy as np

def Clubb2017_qq_threshold(raster, threshold=0.01, plot=False, ax=None):
    values = raster.data.flatten()
    values = values[np.isfinite(values)]
    values = np.sort(values)

    norm_dist = norm_dist_from_percentiles(values, 25, 75)
    #norm_dist = stats.norm(values.std(), values.mean())

    osm, osr = stats.probplot(values, dist=norm_dist, plot=None, fit=False)

    diff = np.abs(osr - osm) / (values.max() - values.min())
    inds = diff < threshold

    ind = None
    if inds.sum():
        ind = np.argwhere(inds)[0].item()

    if plot:
        ax = plot_qq(osm, osr, norm, ind, ax=ax)

    if ind is not None:
        thresh =  values[ind]

    if ax is not None:
        return ax, thresh
    else:
        return thresh
    

def norm_dist_from_percentiles(values, p1, p2):
    p1_val = np.percentile(values, p1)
    p2_val = np.percentile(values, p2)
    z1 = stats.norm.ppf(p1/100)
    z2 = stats.norm.ppf(p2/100)
    std = (p2_val - p1_val) / (z2 - z1)
    mean = p1_val - z1 * std
    norm = stats.norm(std, mean)
    return norm

def plot_qq(osm, osr, norm, ind=None, ax=None):
    if ax is None:
        fig, ax = plt.subplots()

    ax.plot((osm - norm.mean())/norm.std(), osr, 'o', label='empirical')
    ax.plot((osm - norm.mean())/norm.std(), osm, 'r--', label='45 degree line')
    if value is not None:
        ax.axvline(x=(osr[ind] - norm.mean())/norm.std(), color='g', linestyle='--', label= f'{lowest:.2f}')
    return ax
