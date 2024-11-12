# smooth flowlines
# compute xsection points
# observe values
# preprocess profiles
# mark candidate points
# detect wall points
# return df

# preprocessing layers needed:
# geom
# streamID
# pointID
# xsID
# alpha
# flow_path
# hillslope
# dem
# hand
# params needed:
#   min_hand_jump
#   ratio
#   min_peak_prominance
#   min_distance

# for method = max-ascent
# layers needed:
#   curvature
#   slope
# params needed:
#  num_cells
#  slope_threshold

# for method = segment_slope
# layers needed: 
#   curvature
#   slope
# params needed:
#  slope_threshold
#  distance
#  height


# INPUT:
#   dataset
#   method?
#   params
