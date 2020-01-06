# some reusable constants are defined here
# units in mm

pcb_thickness = 1.6

# Standard screw thread paramaters
# https://www.engineersedge.com/hardware/iso_metric_tap_14585.htm
std_screw_threads = {
    "m2": {"r": 2 / 2, "tap_r": 1.6 / 2, "clearance_r": 2.4 / 2, "close_r": 2.2 / 2},
    "m3": {"r": 3 / 2, "tap_r": 2.5 / 2, "clearance_r": 3.4 / 2, "close_r": 3.2 / 2},
    "m4": {"r": 4 / 2, "tap_r": 3.3 / 2, "clearance_r": 4.5 / 2, "close_r": 4.3 / 2},
    "m5": {"r": 5 / 2, "tap_r": 4.2 / 2, "clearance_r": 5.5 / 2, "close_r": 5.3 / 2},
}

# Standard socket screw parameters (ANSI/ASME B18.3.1M, seems equiv. to DIN 912)
# https://www.engineersedge.com/hardware/_metric_socket_head_cap_screws_14054.htm
# https://www.amesweb.info/Screws/CounterboreSizes_MetricSocketHeadCapScrews.aspx
std_socket_screws = {
    "m3": {"cap_r": 5.5 / 2, "cap_h": 3, "cbore_r": 6.50 / 2, "cbore_h": 3},
    "m4": {"cap_r": 7.0 / 2, "cap_h": 4, "cbore_r": 8.25 / 2, "cbore_h": 4},
    "m5": {"cap_r": 8.5 / 2, "cap_h": 5, "cbore_r": 9.75 / 2, "cbore_h": 5},
}

# Standard hex nut parameters (ANSI/ASME B18.2.4.1M, seems equiv. to DIN 934)
# https://www.engineersedge.com/hardware/standard_metric_hex_nuts_13728.htm
std_hex_nuts = {
    "m3": {"hole_r": 3 / 2, "h": 2.4, "flat_w": 5.5, "corner_w": 6.35},
    "m4": {"hole_r": 4 / 2, "h": 3.2, "flat_w": 7.0, "corner_w": 8.08},
    "m5": {"hole_r": 5 / 2, "h": 4.7, "flat_w": 8.0, "corner_w": 9.24},
}

# Standard flanged hex nut parameters (ANSI B18.2.4.4M, seems equiv. to DIN 6923)
# https://www.engineersedge.com/hardware/metric_hex_flange_nuts__13730.htm
std_flanged_hex_nuts = {
    "m5": {
        "hole_r": 5 / 2,
        "h": 5,
        "flat_w": 8.0,
        "corner_w": 9.24,
        "washer_r": 11.8 / 2,
        "washer_h": 1,
    }
}

# Standard washer parameters (ISO 7089, seems equiv. to DIN 125)
# https://www.engineersedge.com/iso_flat_washer.htm
std_washers = {
    "m3": {"r_i": 3.2 / 2, "r_o": 7 / 2, "h": 0.5},
    "m4": {"r_i": 4.3 / 2, "r_o": 9 / 2, "h": 0.8},
    "m5": {"r_i": 5.3 / 2, "r_o": 10 / 2, "h": 1.0},
}

# Standard countersink screw parameters (DIN 7991)
# http://www.dinstock.com/useruploads/files/socket_countersunk_screws_din7991.pdf
std_countersinks = {
    "m5": {
        "cap_r": 11.2 / 2,
        "cap_h": 2.5,
        "csk_r": 11.2 / 2,
        "csk_h": 2.5,
        "angle": 90,
    }
}

# Standard hex socket drivers with 1/4" square drive e.g. Bahco 6700SM-8
# ISO 2725 / 1174
# DIN 3124 / 3120
# https://docs.rs-online.com/4841/0900766b8140d1e5.pdf
# Dict keys are width across flats of hex nut, values are radius of socket
std_sockets = {5.5: 8.7 / 2, 7.0: 10.8 / 2, 8.0: 11.9 / 2}

# Parameters for designing grooves for static o-ring face seals.
# Derived from https:#www.parker.com/Literature/O-Ring Division Literature/ORD 5700.pdf
# "squeeze_fraction" = maximum fractional squeeze of the o-ring cross-section when sealed
# "min_squeeze" = minimum recommended squeeze of the o-ring cross-section in mm when sealed
# "groove_h_fraction" = fractional of o-ring cross-section to use for height of groove
# "groove_w_fraction" = fractional of o-ring cross-section to use for width of groove
# "surface_finish" = recommended minimum surface roughness for o-ring groove in mm
# "max_stretch_fraction" = maximum recommended stretch fraction
# "corner_r_fraction" = minimum recommended fraction of o-ring cross-section to use for inner groove radius i.e. bending radius, p4-3
oring_grooves = {
    "squeeze_fraction": 0.3,
    "min_squeeze": 0.2,
    "groove_h_fraction": 0.7,
    "groove_w_fraction": 1.25,
    "surface_finish": (16 / 1000000) * 2.54,
    "max_stretch_fraction": 0.05,
    "corner_r_fraction": 3,
}

# Standard o-rings parameters in mm (ISO 3601, similar/equiv to BS1806)
# id and cs from https://www.applerubber.com/src/pdf/iso-3601-metric-size-o-rings.pdf
# grooves from https:#www.parker.com/Literature/O-Ring Division Literature/ORD 5700.pdf
std_orings = {
    167: {
        "id": 177.47,
        "cs": 2.62,
        "id_tol": 1.020,
        "cs_tol": 0.080,
        "gland_depth": 0.077 * 25.4,
        "groove_w": 0.1225 * 25.4,
    },
    168: {
        "id": 183.82,
        "cs": 2.62,
        "id_tol": 1.140,
        "cs_tol": 0.080,
        "gland_depth": 0.077 * 25.4,
        "groove_w": 0.1225 * 25.4,
    },
    169: {
        "id": 190.17,
        "cs": 2.62,
        "id_tol": 1.140,
        "cs_tol": 0.080,
        "gland_depth": 0.077 * 25.4,
        "groove_w": 0.1225 * 25.4,
    },
    177: {
        "id": 240.97,
        "cs": 2.62,
        "id_tol": 1.400,
        "cs_tol": 0.080,
        "gland_depth": 0.077 * 25.4,
        "groove_w": 0.1225 * 25.4,
    },
    178: {
        "id": 247.32,
        "cs": 2.62,
        "id_tol": 1.400,
        "cs_tol": 0.080,
        "gland_depth": 0.077 * 25.4,
        "groove_w": 0.1225 * 25.4,
    },
}

# RS Stock No. 908-7532 machine screws are good m5 countersinks

# counterbore hole parameters for use with
# RS flangenut Stock No. 725-9650
cbore_thru_dia = 2 * std_screw_threads["m5"]["close_r"]
cbore_dia = 12
cbore_depth = 6
