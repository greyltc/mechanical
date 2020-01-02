# some reusable constants are defined here

pcb_thickness = 1.6
screw_threads = {
    "m3": {"r": 3 / 2, "tap_r": 2.5 / 2, "clearance_r": 3.4 / 2},
    "m4": {"r": 4 / 2, "tap_r": 3.3 / 2, "clearance_r": 4.5 / 2},
    "m5": {"r": 5 / 2, "tap_r": 4.2 / 2, "clearance_r": 5.5 / 2},
}

# counter sunk hole parameters for use with
# RS Stock No. 908-7532 machine screws
csk_thru_dia = m5_clearance_dia
csk_angle = 82

# counterbore hole parameters for use with
# RS flangenut Stock No. 725-9650
cbore_thru_dia = m5_clearance_dia
cbore_dia = 12
cbore_depth = 6
