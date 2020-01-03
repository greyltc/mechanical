# some reusable constants are defined here
import math

pcb_thickness = 1.6

# Standard screw thread paramaters
# https://www.engineersedge.com/hardware/iso_metric_tap_14585.htm
std_screw_threads = {
    "m3": {"r": 3 / 2, "tap_r": 2.5 / 2, "clearance_r": 3.4 / 2},
    "m4": {"r": 4 / 2, "tap_r": 3.3 / 2, "clearance_r": 4.5 / 2},
    "m5": {"r": 5 / 2, "tap_r": 4.2 / 2, "clearance_r": 5.5 / 2},
}

# Standard socket screw parameters
# https://www.engineersedge.com/hardware/_metric_socket_head_cap_screws_14054.htm
# https://www.amesweb.info/Screws/CounterboreSizes_MetricSocketHeadCapScrews.aspx
std_socket_screws = {
    "m3": {"cap_r": 5.5 / 2, "cap_h": 3, "cbore_r": 6.50 / 2, "cbore_h": 3},
    "m4": {"cap_r": 7.0 / 2, "cap_h": 4, "cbore_r": 8.25 / 2, "cbore_h": 4},
    "m5": {"cap_r": 8.5 / 2, "cap_h": 5, "cbore_r": 9.75 / 2, "cbore_h": 5},
}

# Standard hex nut parameters
# https://www.engineersedge.com/hardware/standard_metric_hex_nuts_13728.htm
std_hex_nuts = {
    "m3": {
        "hole_r": 3 / 2,
        "h": 2.4,
        "side_l": (5.5 / 2) / math.sin(60 * math.pi / 180),
    },
    "m4": {
        "hole_r": 4 / 2,
        "h": 3.2,
        "side_l": (7.0 / 2) / math.sin(60 * math.pi / 180),
    },
    "m5": {
        "hole_r": 5 / 2,
        "h": 4.7,
        "side_l": (8.0 / 2) / math.sin(60 * math.pi / 180),
    },
}

# counter sunk hole parameters for use with
# RS Stock No. 908-7532 machine screws
csk_thru_dia = 2 * std_screw_threads["m5"]["clearance_r"]
csk_angle = 82

# counterbore hole parameters for use with
# RS flangenut Stock No. 725-9650
cbore_thru_dia = 2 * std_screw_threads["m5"]["clearance_r"]
cbore_dia = 12
cbore_depth = 6
