#!/usr/bin/env python3

import cadquery
import geometrics
from geometrics.toolbox.twod_to_threed import TwoDToThreeD
from pathlib import Path
import os


def main():
    # define where we'll read shapes from
    try:
        wrk_dir = Path(__file__).parent
    except Exception as e:
        wrk_dir = Path.cwd()
    print(f"Working directory is {wrk_dir}")
    sources = [
        wrk_dir / "drawings" / "2d.dxf",
    ]

    # instructions for 2d->3d
    instructions = []
    substrate_thickness = 0.3
    copper_thickness = 10
    slot_plate_thickness = 2.3
    pcb_thickness = 1.6
    pusher_thickness = 4
    dowel_length = copper_thickness + slot_plate_thickness + pcb_thickness + pusher_thickness + 2
    wall_height = 28
    clamper_threads_length = 25
    clamper_thread_depth = 5

    # copper base starts at this height
    copper_base_zero = -copper_thickness - slot_plate_thickness

    hole_spacing = 38.35
    cb_diameter = 15.25
    cb_hole_diameter = 11.5

    instructions.append(
        {
            "name": "squirrel",
            "layers": [
                {
                    "name": "dowels",
                    "color": "WHITE",
                    "thickness": dowel_length,
                    "z_base": copper_base_zero,
                    "drawing_layer_names": [
                        "dowel",
                    ],
                },
                {
                    "name": "thermal_plate",
                    "color": "GOLD",
                    "thickness": copper_thickness,
                    "z_base": copper_base_zero,
                    "drawing_layer_names": [
                        "cu_base",
                        "corner_holes",
                        "clamper_threads",  # TODO: close up these thread holes from the bottom
                        "3K7_press",
                    ],
                },
                {
                    "name": "walls",
                    "color": "GRAY55",
                    "thickness": wall_height,
                    "drawing_layer_names": [
                        "walls",
                        "corner_holes",
                    ],
                },
                {
                    "name": "substrates",
                    "color": "SKYBLUE",
                    "thickness": substrate_thickness,
                    "z_base": copper_base_zero + copper_thickness,
                    "drawing_layer_names": [
                        "substrates",
                    ],
                },
                {
                    "name": "slot_plate",
                    "color": "RED",
                    "thickness": slot_plate_thickness,
                    "z_base": copper_base_zero + copper_thickness,
                    "drawing_layer_names": [
                        "slot_plate",
                        "clamper_clearance",
                        "3C9_slide",
                    ],
                },
                {
                    "name": "pcb",
                    "color": "DARKGREEN",
                    "thickness": pcb_thickness,
                    "drawing_layer_names": [
                        "pcb",
                        "clamper_clearance",
                    ],
                },
                {
                    "name": "pusher",
                    "color": "GREEN",
                    "thickness": pusher_thickness,
                    "drawing_layer_names": [
                        "pusher",
                        "clamper_clearance",
                        "3C9_slide",
                    ],
                },
                {
                    "name": "clamper_screws",
                    "color": "WHITE",
                    "thickness": clamper_threads_length,
                    "z_base": copper_base_zero + copper_thickness - clamper_thread_depth,
                    "drawing_layer_names": [
                        "clamper_threads",
                    ],
                },
                {
                    "name": "passthrough",
                    "color": "DARKGREEN",
                    "thickness": pcb_thickness,
                    "z_base": copper_base_zero + copper_thickness + slot_plate_thickness,
                    "drawing_layer_names": [
                        "pcb2",
                    ],
                },
            ],
        }
    )

    ttt = TwoDToThreeD(instructions=instructions, sources=sources)
    to_build = [""]
    asys = ttt.build(to_build)

    # real_pcb = geometrics.toolbox.u.import_step(wrk_dir.joinpath("components", "pcb.step"))

    TwoDToThreeD.outputter(asys, wrk_dir)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
