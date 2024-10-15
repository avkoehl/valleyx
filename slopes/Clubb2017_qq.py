"""
https://esurf.copernicus.org/articles/5/369/2017/esurf-5-369-2017.pdf
"""
import matplotlib.pyplot as plt
import scipy.stats as stats
import numpy as np

def Clubb2017_qq_threshold(raster, diff_threshold=0.01, plot=False, ax=None):
    values = raster.data.flatten()
    values = values[np.isfinite(values)]
    values = np.sort(values)

    norm_dist = norm_dist_from_percentiles(values, 25, 75)
    #norm_dist = stats.norm(values.std(), values.mean())

    osm, osr = stats.probplot(values, dist=norm_dist, plot=None, fit=False)

    diff = np.abs(osr - osm) / (values.max() - values.min())
    inds = diff < diff_threshold

    ind = None
    value_threshold = None
    if inds.sum():
        ind = np.argmax(inds)
        value_threshold =  values[ind]

    if plot:
        ax = plot_qq(osm, osr, norm_dist, ind, ax=ax)

    if ax is not None:
        return ax, value_threshold
    else:
        return value_threshold
    

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

    ax.plot((osm - norm.mean())/norm.std(), osr, 'o', label='empirical', markersize=2)
    ax.plot((osm - norm.mean())/norm.std(), osm, 'r--', label='45 degree line')

    if ind is not None:
        x_val = (osr[ind] - norm.mean()) / norm.std()
        ax.axvline(x=x_val, color='b', linestyle='--')

        ax.set_xlim(left=ax.get_xlim()[0], right=ax.get_xlim()[1])
        ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[1])

        ax.fill_betweenx(ax.get_ylim(), ax.get_xlim()[0], x_val, color='lightblue', alpha=0.4)
        #ax.fill_betweenx(ax.get_ylim(), ax.get_xlim()[1], color='white')

    ax.grid(True)

    return ax
