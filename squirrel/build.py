#!/usr/bin/env python3

import cadquery
import cadquery as cq
from cadquery import CQ
from geometrics.toolbox.twod_to_threed import TwoDToThreeD
from geometrics.toolbox.utilities import import_step
from geometrics.toolbox import groovy
from pathlib import Path
from cq_warehouse.fastener import SocketHeadCapScrew, HexNut, SetScrew, CounterSunkScrew
import cq_warehouse.extensions  # this does something even though it's not directly used
import math
import itertools


def main():
    # set working directory
    try:
        wrk_dir = Path(__file__).parent
    except Exception as e:
        wrk_dir = Path.cwd()
    print(f"Working directory is {wrk_dir}")
    sources = [
        wrk_dir / "drawings" / "2d.dxf",
    ]

    cq.Workplane.mk_groove = groovy.mk_groove

    # instructions for 2d->3d
    instructions = []
    substrate_thickness = 0.3
    copper_thickness = 15
    thermal_pedestal_height = 14.1
    slot_plate_thickness = 2.3
    pcb_thickness = 1.6
    pusher_thickness = 4
    dowel_length = slot_plate_thickness + pcb_thickness + pusher_thickness + thermal_pedestal_height + 3  # nominally 25
    wall_height = 28
    passthrough_standoff_height = 15
    hardware_color = "GRAY75"

    # base posision of the pedistal now
    copper_base_zero = -copper_thickness - thermal_pedestal_height - slot_plate_thickness

    as_name = "squirrel"
    instructions.append(
        {
            "name": as_name,
            "layers": [
                {
                    "name": "dowels",
                    "color": hardware_color,
                    "thickness": dowel_length,
                    "z_base": copper_base_zero + copper_thickness,
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
                    "color": "BLUE",
                    "thickness": substrate_thickness,
                    "z_base": copper_base_zero + copper_thickness + thermal_pedestal_height,
                    "drawing_layer_names": [
                        "substrates",
                    ],
                },
                {
                    "name": "slot_plate",
                    "color": "RED",
                    "thickness": slot_plate_thickness,
                    "z_base": copper_base_zero + copper_thickness + thermal_pedestal_height,
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
                    "name": "passthrough",
                    "color": "DARKGREEN",
                    "thickness": pcb_thickness,
                    "z_base": copper_base_zero + copper_thickness + passthrough_standoff_height,
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

    no_threads = True  # set true to make all the hardware have no threads (much faster, smaller)
    center_shift = (-4.5, 0)
    wall_outer = (229, 180)
    corner_holes_offset = 7.5
    corner_hole_points = [(x * (wall_outer[0] - 2 * corner_holes_offset) - (wall_outer[0] - 2 * corner_holes_offset) / 2 + center_shift[0], y * (wall_outer[1] - 2 * corner_holes_offset) - (wall_outer[1] - 2 * corner_holes_offset) / 2 + center_shift[1]) for x, y in itertools.product(range(0, 2), range(0, 2))]
    assembly_screw_length = 45
    corner_screw = SocketHeadCapScrew(size="M6-1", fastener_type="iso4762", length=assembly_screw_length, simple=no_threads)

    base_outer = (wall_outer[0] + 40, wall_outer[1])

    cop = {"centerOption": "ProjectedOrigin"}
    cob = {"centerOption": "CenterOfBoundBox"}

    def mkbase(
        aso: cadquery.Assembly,
        thickness: float,
        cshift,
        extents,
        hps,
        screw: SocketHeadCapScrew,
        pedistal_height: float,
        zbase: float,
    ):
        """the thermal base"""
        plate_name = "thermal_plate"
        vac_name = "vacuum_chuck"
        color = cadquery.Color("GOLD")
        fillet = 2
        chamfer = 1
        corner_screw_depth = 2

        pedistal_xy = (161, 152)
        pedistal_fillet = 10

        dowelpts = [(-73, -66), (73, 66)]
        dowel_nominal_d = 3  # marked on drawing for pressfit with ⌀3K7

        # vac chuck clamp screws
        vacscrew_length = 20
        vacscrew = CounterSunkScrew(size="M6-1", fastener_type="iso14581", length=vacscrew_length, simple=no_threads)
        vacclamppts = [(-73, -54.75), (-73, 54.75), (73, -54.75), (73, 54.75)]

        # dummy screw for vac fitting
        vac_fitting_screw = SetScrew("M5-0.8", fastener_type="iso4026", length=30, simple=no_threads)

        # setscrew clamping stuff
        setscrew_len = 30
        screw_well_depth = 3
        setscrew_recess = pedistal_height + screw_well_depth
        setscrew = SetScrew(size="M6-1", fastener_type="iso4026", length=setscrew_len, simple=no_threads)
        setscrewpts = [(-73, -43.5), (73, 43.5)]

        # waterblock nuts and holes
        wb_w = 177.8
        wb_mount_offset_from_edge = 7.25
        wb_mount_offset = wb_w / 2 - wb_mount_offset_from_edge
        waterblock_mount_nut = HexNut(size="M6-1", fastener_type="iso4033", simple=no_threads)
        wb_mount_points = [
            (120, wb_mount_offset),
            (120, -wb_mount_offset),
            (-129, wb_mount_offset),
            (-129, -wb_mount_offset),
        ]

        wp = CQ().workplane(**cop, offset=zbase).sketch()
        wp = wp.push([cshift]).rect(extents[0], extents[1], mode="a").reset().vertices().fillet(fillet)
        wp = wp.finalize().extrude(thickness)
        wp: cadquery.Workplane  # shouldn't have to do this (needed for type hints)

        # pedistal
        wp = wp.faces(">Z").workplane(**cop).sketch().rect(*pedistal_xy).reset().vertices().fillet(pedistal_fillet)
        wp = wp.finalize().extrude(pedistal_height)

        hardware = cq.Assembly(None)  # a place to keep the harware

        # corner screws
        wp = wp.faces("<Z").workplane(**cop, offset=-corner_screw_depth).pushPoints(hps).clearanceHole(fastener=screw, baseAssembly=hardware)
        wp = wp.faces("<Z[-2]").wires().toPending().extrude(corner_screw_depth, combine="cut")  # make sure the recessed screw is not buried

        # dowel holes
        wp = wp.faces(">Z").workplane(**cop).pushPoints(dowelpts).hole(dowel_nominal_d, depth=pedistal_height)

        # waterblock mounting
        wp = wp.faces(">Z[-2]").workplane(**cop).pushPoints(wb_mount_points).clearanceHole(fastener=waterblock_mount_nut, counterSunk=False, baseAssembly=hardware)

        # vac chuck stuff
        # split
        wp = wp.faces(">Z[-2]").workplane(**cop).split(keepTop=True, keepBottom=True).clean()
        btm_piece = wp.solids("<Z").first().edges("not %CIRCLE").chamfer(chamfer)
        top_piece = wp.solids(">Z").first().edges("not %CIRCLE").chamfer(chamfer)

        # hole array
        n_array_x = 4
        n_array_y = 5
        x_spacing = 35
        y_spacing = 29
        x_start = (n_array_x - 1) / 2
        y_start = (n_array_y - 1) / 2

        n_sub_array_x = 8
        n_sub_array_y = 2
        x_spacing_sub = 3
        y_spacing_sub = 10
        x_start_sub = (n_sub_array_x - 1) / 2
        y_start_sub = (n_sub_array_y - 1) / 2

        hole_d = 1
        hole_cskd = 1.1
        csk_ang = 45

        # compute all the vac chuck vent hole points
        vac_hole_pts = []  # where the vac holes are drilled
        street_centers = []  # the distribution street y values
        for i in range(n_array_x):
            for j in range(n_array_y):
                for k in range(n_sub_array_x):
                    for l in range(n_sub_array_y):
                        ctrx = (i - x_start) * x_spacing
                        ctry = (j - y_start) * y_spacing
                        offx = (k - x_start_sub) * x_spacing_sub
                        offy = (l - y_start_sub) * y_spacing_sub
                        vac_hole_pts.append((ctrx + offx, ctry + offy))
                        street_centers.append((0, ctry + offy))
        street_centers = list(set(street_centers))  # prune duplicates

        # drill all the vac holes
        top_piece = CQ(top_piece.findSolid()).faces(">Z").workplane(**cop).pushPoints(vac_hole_pts).cskHole(diameter=hole_d, cskDiameter=hole_cskd, cskAngle=csk_ang)

        # clamping setscrew threaded holes
        # wp = wp.faces(">Z").workplane().pushPoints(setscrewpts).tapHole(setscrew, depth=setscrew_recess, baseAssembly=hardware)  # bug prevents this from working correctly, workaround below
        top_piece = top_piece.faces(">Z").workplane(offset=setscrew_len - setscrew_recess).pushPoints(setscrewpts).tapHole(setscrew, depth=setscrew_len, baseAssembly=hardware)
        btm_piece = CQ(btm_piece.findSolid()).faces(">Z").workplane(**cop).pushPoints(setscrewpts).circle(vacscrew.clearance_hole_diameters["Close"] / 2).cutBlind(-screw_well_depth)

        # vac chuck clamping screws
        top_piece = top_piece.faces(">Z").workplane(**cop).pushPoints(vacclamppts).clearanceHole(vacscrew, fit="Close", baseAssembly=hardware)
        btm_piece = btm_piece.faces(">Z").workplane(**cop).pushPoints(vacclamppts).tapHole(vacscrew, depth=vacscrew_length - pedistal_height + 1)

        # compute the hole array extents for o-ring path finding
        sub_x_length = (n_sub_array_x - 1) * x_spacing_sub + hole_d
        array_x_length = (n_array_x - 1) * x_spacing + sub_x_length

        sub_y_length = (n_sub_array_y - 1) * y_spacing_sub + hole_d
        array_y_length = (n_array_y - 1) * y_spacing + sub_y_length

        # vac connection stuff
        vac_fitting_loc_offset = -0.5 * y_spacing

        # takes 4mm OD tubes, needs M5x0.8 threads, part number 326-8956
        fitting_tap_depth = 20
        a_vac_fitting = import_step(wrk_dir.joinpath("components", "3118_04_19.step"))
        a_vac_fitting = a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(1, 0, 0), angleDegrees=90).translate((0, 0, 1.5))
        vac_chuck_fitting = cadquery.Assembly(a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=-3), name="one_vac_fitting")
        top_piece = top_piece.faces(">X").workplane(**cob).center(vac_fitting_loc_offset, 0).tapHole(vac_fitting_screw, depth=fitting_tap_depth)
        vac_chuck_fitting.loc = top_piece.plane.location
        hardware.add(vac_chuck_fitting, name="vac chuck fitting")

        # vac distribution network
        zdrill_loc = (pedistal_xy[0] / 2 - fitting_tap_depth, 0.5 * y_spacing)
        zdrill_r = 3
        zdrill_depth = -pedistal_height / 2 - 2.5
        top_piece = top_piece.faces("<Z").workplane(**cob).pushPoints([zdrill_loc]).circle(zdrill_r).cutBlind(zdrill_depth)

        highway_depth = 3
        highway_width = 6
        street_depth = 2
        street_width = 1
        top_piece = top_piece.faces("<Z").workplane(**cob).sketch().push([(zdrill_loc[0] / 2, zdrill_loc[1])]).slot(w=zdrill_loc[0], h=highway_width).finalize().cutBlind(-highway_depth)
        top_piece = top_piece.faces("<Z").workplane(**cob).sketch().slot(w=pedistal_xy[0] - 2 * fitting_tap_depth, h=highway_width, angle=90).finalize().cutBlind(-highway_depth)  # cut center highway
        top_piece = top_piece.faces("<Z").workplane(**cob).sketch().push(street_centers).slot(w=array_x_length - hole_d, h=street_width).finalize().cutBlind(-street_depth)  # cut streets

        # padding to keep the oring groove from bothering the vac holes
        groove_x_pad = 8
        groove_y_pad = 16

        # that's part number 196-4941
        o_ring_thickness = 2
        o_ring_inner_diameter = 170

        # cut the o-ring groove
        top_piece = top_piece.faces("<Z").workplane(**cob).mk_groove(ring_cs=o_ring_thickness, follow_pending_wires=False, ring_id=o_ring_inner_diameter, gland_x=array_x_length + groove_x_pad, gland_y=array_y_length + groove_y_pad, hardware=hardware)

        aso.add(btm_piece, name=plate_name, color=color)
        aso.add(top_piece, name=vac_name, color=color)
        aso.add(hardware.toCompound(), name="hardware", color=cadquery.Color(hardware_color))

    mkbase(asys[as_name], copper_thickness, center_shift, base_outer, corner_hole_points, corner_screw, thermal_pedestal_height, copper_base_zero)

    def mkwalls(
        aso: cadquery.Assembly,
        height: float,
        cshift,
        extents,
        hps,
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
        chamfer = 1

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
        wp = wp.faces(">Z").workplane(**cop, offset=-nut.nut_thickness).pushPoints(hps).clearanceHole(fastener=nut, counterSunk=False, baseAssembly=wall_hardware)
        wp = wp.faces(">Z").workplane(**cop).sketch().push(hps[0:4:3]).rect(flat_to_flat, nut.nut_diameter, angle=45).reset().push(hps[1:3]).rect(flat_to_flat, nut.nut_diameter, angle=-45).reset().vertices().fillet(nut.nut_diameter / 4).finalize().cutBlind(-nut.nut_thickness)

        # chamfers
        wp = wp.faces(">Z").edges(">>X").chamfer(chamfer)

        # gas holes
        wp = wp.faces("<X").workplane(**cob).center(back_holes_shift, 0).rarray(back_holes_spacing, 1, 2, 1).cboreHole(diameter=cb_hole_diameter, cboreDiameter=cb_diameter, cboreDepth=cbd, depth=thickness)
        wp = wp.faces(">X").workplane(**cob).rarray(front_holes_spacing, 1, 2, 1).cboreHole(diameter=cb_hole_diameter, cboreDiameter=cb_diameter, cboreDepth=cbd, depth=thickness)

        # that's part number polymax 230X2N70
        o_ring_thickness = 2
        o_ring_inner_diameter = 230
        ooffset = 8

        # cut the lid o-ring groove
        wp = wp.faces(">Z").workplane(**cob).mk_groove(ring_cs=o_ring_thickness, follow_pending_wires=False, ring_id=o_ring_inner_diameter, gland_x=extents[0] - ooffset, gland_y=extents[1] - ooffset, hardware=wall_hardware)

        # cut the base o-ring groove
        wp = wp.faces("<Z").workplane(**cob).mk_groove(ring_cs=o_ring_thickness, follow_pending_wires=False, ring_id=o_ring_inner_diameter, gland_x=extents[0] - ooffset, gland_y=extents[1] - ooffset, hardware=wall_hardware)

        aso.add(wp, name=name, color=color)

        pipe_fitting_asy = cadquery.Assembly(import_step(wrk_dir.joinpath("components", "5483T93_Miniature Nickel-Plated Brass Pipe Fitting.step")).translate((0, 0, -6.35)), name="one_pipe_fitting")

        # move the pipe fittings to their wall holes
        wppf = wp.faces(">X").workplane(**cob).center(front_holes_spacing / 2, 0)
        pipe_fitting_asy.loc = wppf.plane.location
        wall_hardware.add(pipe_fitting_asy, name="front_right_gas_fitting")
        wppf = wppf.center(-front_holes_spacing, 0)
        pipe_fitting_asy.loc = wppf.plane.location
        wall_hardware.add(pipe_fitting_asy, name="front_left_gas_fitting")
        wppf = wp.faces("<X").workplane(**cob).center(back_holes_shift + back_holes_spacing / 2, 0)
        pipe_fitting_asy.loc = wppf.plane.location
        wall_hardware.add(pipe_fitting_asy, name="rear_left_gas_fitting")
        wppf = wppf.center(-back_holes_spacing, 0)
        pipe_fitting_asy.loc = wppf.plane.location
        wall_hardware.add(pipe_fitting_asy, name="rear_right_gas_fitting")

        aso.add(wall_hardware.toCompound(), name="wall_hardware", color=cadquery.Color(hardware_color))

    mkwalls(asys[as_name], wall_height, center_shift, wall_outer, corner_hole_points, copper_base_zero + copper_thickness)

    TwoDToThreeD.outputter(asys, wrk_dir)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
