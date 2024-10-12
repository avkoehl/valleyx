"""
input: bps, labels

slope series (detrended)?
detrended elevation series


cases:
    channel is valley
    wall point only on one side
    wall points both sides
    no wall points

slope threshold = 10
max_height_feature (terrace, island, bar, fan, tallus, morraine)... 10


wall point:
    start of a segment with slope exceeding threshold not leading to a valley floor feature

slope unit patterns:

slope up means when on the axis perpendicular to the channel start to end increases in elevation relative to stream

    1. flat, slope_up, flat, slope_up -- terrace/fan/tallus
    2. flat, slope_up, flat, slope_down, flat/slope -- island/morraine/ -- how to distinguish from another valley?
    2. flat, slope_up, slope_down, flat/slope -- island/morraine/ -- how to distinguish from another valley?

    slope_up, slope_up -- no floor
   NO TERRACE,  slope_up, flat, slope_up, NO TERRACE -- floor
"""

def slope_units(slope, labels, bps):
    return

def group_slope_units():
    return

def classify_slope_units(slope, detrended_elev, bps):
    return
