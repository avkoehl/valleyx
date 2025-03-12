from dataclasses import dataclass
from dataclasses import field
from typing import Optional


@dataclass
class ReachConfig:
    """Parameters for Reach Detection

    Parameters
    ----------
    hand_threshold : float, default=10
        Constant elvation threshold for approximating the valley bottoms
    spacing : int, default=20
        Spacing along the centerline to sample the width of the valley
    minsize : int, default=200
        Minimum length of a reach in meters, shorter reaches are appended to
        the previous reach
    window : int, default=5
        Window for smoothing width measurements, value is the number of
        observations to average
    """

    hand_threshold: float = 10  #  meters
    spacing: int = 20  #  meters
    minsize: int = 300  #  meters
    window: int = 5  #  observations


@dataclass
class FoundationConfig:
    """Parameters for the Low Slope Connectivity Algorithm

    Parameters
    ----------
    sigma: float, default=5
        Standard deviation for gaussian smoothing of the dem
    slope: float, default=3.5
        Maximum slope in degrees to be considered a valley floor
    """

    sigma: float = 5
    slope: float = 5  # degrees


@dataclass
class FloodConfig:
    """Parameters for the Flood Threshold Algorithm

    Parameters
    ----------
    xs_spacing : int, default=20
        Distance along the flowline between cross sections in meters
    xs_max_width : int, default=500
        Distance perpendicular to the flowline to extend the cross section in
        each direction in meters. The total width of the cross section is 2 *
        xs_width. Called max width because the cross section is not guaranteed
        to reach this width since it is limited by the catchment boundary.
    point_spacing : int, default=10
        Distance between points along the cross section in meters
    min_hand_jump : int, default=15
        Minimum height above drainage difference between pixels to be
        considered a peak
    ratio : float, default=3.5
        Minimum ratio between the change in HAND and the change in elevation to
        be considered a peak
    min_peak_prominence : int, default=20
        Minimum prominence of a peak to be considered a peak
    min_distance : int, default=20
        Minimum required distance from stream center in meters for the cross
        section to be considered
    path_length : float, default=50
        Length of the sustained slope path in meters
    slope_threshold : float, default=10
        Minimum slope in degrees to be considered a sustained slope
    default_threshold : float, default=5
        Default threshold for hand thresholding. Used when min_points is not
        met for the reach
    buffer : float, default=1
        Buffer to add to the thresholded value
    percentile : float, default=0.80
        Percentile for the hand threshold
    min_points : int, default=5
        Minimum number of points to use for hand thresholding
    """

    # cross section parameters
    xs_spacing: int = 20  # meters
    xs_max_width: int = 500  # meters
    point_spacing: int = 10  # meters

    # cross section preprocessing
    min_hand_jump: int = 15  # meters
    ratio: float = 3.5
    min_peak_prominence: int = 20  # meters
    min_distance: int = 20  # meters

    # sustained slope parameters
    path_length: float = 50  # meters
    slope_threshold: float = 10  # degrees slope

    # hand thresholding parameters
    default_threshold: float = 5  # meters
    buffer: float = 1  # meters
    percentile: float = 0.80  # percentile
    min_points: int = 5


@dataclass
class FloorConfig:
    """Parameters for the Floor Detection Algorithm
    Parameters
    ----------
    max_floor_slope : float, default=None
        Cells exceeding this slope are removed from the floor
    max_floor_slope : float, default=None
        Holes in the floor smaller than this area are filled
    foundation : FoundationConfig
        Configuration for the Low Slope Connectivity Algorithm. Run
        help(FoundationConfig) for details
    flood : FloodConfig
        Configuration for the Flood Threshold Algorithm. Run help(FloodConfig)
        for details
    """

    max_floor_slope: Optional[float] = None
    max_fill_area: Optional[float] = None
    foundation: FoundationConfig = field(default_factory=FoundationConfig)
    flood: FloodConfig = field(default_factory=FloodConfig)


@dataclass
class ValleyConfig:
    """Complete Configuration for the Valley Detection Algorithm
    Parameters
    ----------
    reach : ReachConfig
        Configuration for the Reach Detection Algorithm. Run help(ReachConfig)
        for details
    floor : FloorConfig
        Configuration for the Floor Detection Algorithm. Run help(FloorConfig)
        for details

    Examples
    --------
    Create a configuration with default parameters:

    >>> config = ValleyConfig()

    Create a configuration with custom parameters:

    >>> config = ValleyConfig()
    >>> config.reach.hand_threshold = 15

    """

    reach: ReachConfig = field(default_factory=ReachConfig)
    floor: FloorConfig = field(default_factory=FloorConfig)
