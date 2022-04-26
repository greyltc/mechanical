#!/usr/bin/env python3

import cadquery
import cadquery as cq
from cadquery import CQ
from geometrics.toolbox.twod_to_threed import TwoDToThreeD
from geometrics.toolbox.utilities import import_step
from pathlib import Path
from cq_warehouse.fastener import SocketHeadCapScrew, HexNut, ButtonHeadScrew, SetScrew
import cq_warehouse.extensions
import math
import itertools


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
    thermal_pedestal_height = 10
    slot_plate_thickness = 2.3
    pcb_thickness = 1.6
    pusher_thickness = 4
    dowel_length = copper_thickness + slot_plate_thickness + pcb_thickness + pusher_thickness + thermal_pedestal_height + 2
    wall_height = 28
    clamper_threads_length = 25
    clamper_thread_depth = 5

    # copper base starts at this height
    copper_base_zero = -copper_thickness - slot_plate_thickness

    as_name = "squirrel"
    instructions.append(
        {
            "name": as_name,
            "layers": [
                {
                    "name": "dowels",
                    "color": "WHITE",
                    "thickness": dowel_length,
                    "z_base": copper_base_zero - thermal_pedestal_height,
                    "drawing_layer_names": [
                        "dowel",
                    ],
                },
                # {
                #     "name": "thermal_plate2",
                #     "color": "GOLD",
                #     "thickness": copper_thickness,
                #     "z_base": copper_base_zero,
                #     "drawing_layer_names": [
                #         "cu_base",
                #         "corner_holes",
                #         "clamper_threads",  # TODO: close up these thread holes from the bottom
                #         "3K7_press",
                #     ],
                # },
                # {
                #     "name": "walls2",
                #     "color": "GRAY55",
                #     "thickness": wall_height,
                #     "drawing_layer_names": [
                #         "walls",
                #         "corner_holes",
                #     ],
                # },
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
                # {
                #     "name": "clamper_screws",
                #     "color": "WHITE",
                #     "thickness": clamper_threads_length,
                #     "z_base": copper_base_zero + copper_thickness - clamper_thread_depth,
                #     "drawing_layer_names": [
                #         "clamper_threads",
                #     ],
                # },
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

    no_threads = False  # set true to make all the hardware have no threads (much faster, smaller)
    center_shift = (-4.5, 0)
    wall_outer = (229, 180)
    corner_holes_offset = 7.5
    corner_hole_points = [(x * (wall_outer[0] - 2 * corner_holes_offset) - (wall_outer[0] - 2 * corner_holes_offset) / 2 + center_shift[0], y * (wall_outer[1] - 2 * corner_holes_offset) - (wall_outer[1] - 2 * corner_holes_offset) / 2 + center_shift[1]) for x, y in itertools.product(range(0, 2), range(0, 2))]
    assembly_screw_length = 45
    corner_screw = SocketHeadCapScrew(size="M6-1", fastener_type="iso4762", length=assembly_screw_length, simple=no_threads)

    base_outer = (wall_outer[0] + 40, wall_outer[1])

    def mkbase(
        aso: cadquery.Assembly,
        thickness: float,
        cshift,
        extents,
        hps,
        screw: SocketHeadCapScrew,
        pedistal_height,
        zbase: float,
    ):
        """the thermal base"""
        name = "thermal_plate"
        color = cadquery.Color("GOLD")
        fillet = 2

        pedistal_xy = (161, 152)
        pedistal_fillet = 10

        dowelpts = [(-73, -66), (73, 66)]
        dowel_nominal_d = 3  # marked on drawing for pressfit with ⌀3K7

        # clamping stuff
        setscrew_len = 25
        setscrew_recess = 12
        setscrew = SetScrew(size="M6-1", fastener_type="iso4026", length=setscrew_len, simple=no_threads)
        setscrewpts = [(-73, -43.5), (73, 43.5)]

        # waterblock screws
        wb_screw_len = 25
        waterblock_mount_screw = SocketHeadCapScrew(size="M6-1", fastener_type="iso4762", length=wb_screw_len, simple=no_threads)
        wb_mount_screw_points = [
            (120, 80),
            (120, -80),
            (-129, 80),
            (-129, -80),
        ]

        wp = CQ().workplane(offset=zbase).sketch()
        wp = wp.push([cshift]).rect(extents[0], extents[1], mode="a").reset().vertices().fillet(fillet)
        wp = wp.finalize().extrude(thickness)
        wp: cadquery.Workplane  # shouldn't have to do this (needed for type hints)

        # pedistal
        wp = wp.faces(">Z").workplane().sketch().rect(*pedistal_xy).reset().vertices().fillet(pedistal_fillet)
        wp = wp.finalize().extrude(pedistal_height)
        wp: cadquery.Workplane  # shouldn't have to do this (needed for type hints)

        hardware = cq.Assembly(None)  # a place to keep the harware

        # corner screws
        wp = wp.faces("<Z").workplane().pushPoints(hps).clearanceHole(fastener=screw, baseAssembly=hardware)

        # dowel holes
        wp = wp.faces(">Z").workplane().pushPoints(dowelpts).hole(dowel_nominal_d)

        # clamping setscrew threaded holes
        # wp = wp.faces(">Z").workplane().pushPoints(setscrewpts).tapHole(setscrew, depth=setscrew_recess, baseAssembly=hardware)  # bug prevents this from working correctly, workaround below
        wp = wp.faces(">Z").workplane(offset=setscrew_len - setscrew_recess).pushPoints(setscrewpts).tapHole(setscrew, depth=setscrew_recess, baseAssembly=hardware)

        # waterblock mounting
        wp = wp.faces(">Z[-2]").workplane().pushPoints(wb_mount_screw_points).clearanceHole(fastener=waterblock_mount_screw, baseAssembly=hardware)

        aso.add(wp, name=name, color=color)
        aso.add(hardware.toCompound(), name="hardware")

    mkbase(asys[as_name], copper_thickness, center_shift, base_outer, corner_hole_points, corner_screw, thermal_pedestal_height, copper_base_zero - thermal_pedestal_height)

    def mkwalls(
        aso: cadquery.Assembly,
        height: float,
        cshift,
        extents,
        hps,
        screw: SocketHeadCapScrew,
        zbase: float,
    ):
        """the chamber walls"""
        name = "walls"
        color = cadquery.Color("GRAY55")
        thickness = 12
        inner = (extents[0] - 2 * thickness, extents[1] - 2 * thickness)
        inner_shift = cshift
        outer_fillet = 2
        inner_fillet = 15

        nut = HexNut(size="M6-1", fastener_type="iso4033")
        flat_to_flat = math.sin(60 * math.pi / 180) * nut.nut_diameter

        cb_hole_diameter = 20.6375
        cb_diameter = 22.22
        cbd = 1.05  # TODO:change this to compress o-ring properly

        back_holes_shift = 32
        back_holes_spacing = 35
        front_holes_spacing = 60

        wp = CQ().workplane(offset=zbase).sketch()
        wp = wp.push([cshift]).rect(extents[0], extents[1], mode="a").reset().vertices().fillet(outer_fillet)
        wp = wp.push([inner_shift]).rect(inner[0], inner[1], mode="s").reset().vertices().fillet(inner_fillet)
        wp = wp.finalize().extrude(height)
        wp: cadquery.Workplane  # shouldn't have to do this (needed for type hints)

        wall_hardware = cq.Assembly(None, name="wall_hardware")

        # corner holes (with nuts and nut pockets)
        wp = wp.faces(">Z").workplane(offset=-nut.nut_thickness).pushPoints(hps).clearanceHole(fastener=nut, counterSunk=False, baseAssembly=wall_hardware)
        wp = wp.faces(">Z").workplane().sketch().push(hps[0:4:3]).rect(flat_to_flat, nut.nut_diameter, angle=45).reset().push(hps[1:3]).rect(flat_to_flat, nut.nut_diameter, angle=-45).reset().vertices().fillet(nut.nut_diameter / 4).finalize().cutBlind(-nut.nut_thickness)

        # gas holes
        wp = wp.faces("<X").workplane(centerOption="CenterOfBoundBox").center(back_holes_shift, 0).rarray(back_holes_spacing, 1, 2, 1).cboreHole(diameter=cb_hole_diameter, cboreDiameter=cb_diameter, cboreDepth=cbd, depth=thickness)
        wp = wp.faces(">X").workplane(centerOption="CenterOfBoundBox").rarray(front_holes_spacing, 1, 2, 1).cboreHole(diameter=cb_hole_diameter, cboreDiameter=cb_diameter, cboreDepth=cbd, depth=thickness)

        aso.add(wp, name=name, color=color)

        pipe_fitting = import_step(wrk_dir.joinpath("components", "5483T93_Miniature Nickel-Plated Brass Pipe Fitting.step")).translate((0, 0, -6.35))

        hardware_list = []
        wppf = wp.faces(">X").workplane(centerOption="CenterOfBoundBox").center(front_holes_spacing / 2, 0)
        hardware_list += [v.located(wppf.plane.location) for v in pipe_fitting.solids().objects]
        wppf = wp.faces(">X").workplane(centerOption="CenterOfBoundBox").center(-front_holes_spacing / 2, 0)
        hardware_list += [v.located(wppf.plane.location) for v in pipe_fitting.solids().objects]
        wppf = wp.faces("<X").workplane(centerOption="CenterOfBoundBox").center(back_holes_shift - back_holes_spacing / 2, 0)
        hardware_list += [v.located(wppf.plane.location) for v in pipe_fitting.solids().objects]
        wppf = wp.faces("<X").workplane(centerOption="CenterOfBoundBox").center(back_holes_shift + back_holes_spacing / 2, 0)
        hardware_list += [v.located(wppf.plane.location) for v in pipe_fitting.solids().objects]

        wall_hardware.add(cadquery.Compound.makeCompound(hardware_list))

        aso.add(wall_hardware.toCompound(), name="wall_hardware")

    mkwalls(asys[as_name], wall_height, center_shift, wall_outer, corner_hole_points, corner_screw, copper_base_zero + copper_thickness - thermal_pedestal_height)

    TwoDToThreeD.outputter(asys, wrk_dir)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
