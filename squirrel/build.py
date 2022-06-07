#!/usr/bin/env python3

import cadquery
import cadquery as cq
from cadquery import CQ
from geometrics.toolbox.twod_to_threed import TwoDToThreeD
import geometrics.toolbox.utilities as u
from geometrics.toolbox import groovy
from geometrics.toolbox import passthrough
from pathlib import Path
from cq_warehouse.fastener import SocketHeadCapScrew, HexNut, SetScrew, CounterSunkScrew, HexNutWithFlange, CheeseHeadScrew, PanHeadScrew
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

    cq.Workplane.mk_groove = groovy.mk_groove  # add in our groovemaker
    cq.Workplane.make_oringer = passthrough.make_oringer  # add in our passthrough maker

    # instructions for 2d->3d
    instructions = []
    substrate_raise = 0.25
    substrate_thickness = 0.3
    copper_thickness = 15
    thermal_pedestal_height = 14.1
    slot_plate_thickness = 2.3 + substrate_raise
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
                {
                    "name": "substrates",
                    "color": "BLUE",
                    "thickness": substrate_thickness,
                    "z_base": copper_base_zero + copper_thickness + thermal_pedestal_height + substrate_raise,
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
                # {
                #     "name": "pcb",
                #     "color": "DARKGREEN",
                #     "thickness": pcb_thickness,
                #     "z_base": copper_base_zero + copper_thickness + thermal_pedestal_height + slot_plate_thickness,
                #     "drawing_layer_names": [
                #         "pcb",
                #         "clamper_clearance",
                #     ],
                # },
                {
                    "name": "pusher",
                    "color": "GREEN",
                    "thickness": pusher_thickness,
                    "z_base": copper_base_zero + copper_thickness + thermal_pedestal_height + slot_plate_thickness + pcb_thickness,
                    "drawing_layer_names": [
                        "pusher",
                        "clamper_clearance",
                        "3C9_slide",
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
    corner_screw = CheeseHeadScrew(size="M5-0.8", fastener_type="iso14580", length=assembly_screw_length, simple=no_threads)  # SHC-M5-45-A2

    base_outer = (wall_outer[0] + 40, wall_outer[1])

    # get vac fitting geometry
    # takes 4mm OD tubes, needs M5x0.8 threads, part number 326-8956
    a_vac_fitting = u.import_step(wrk_dir.joinpath("components", "3118_04_19.step"))
    a_vac_fitting = a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(1, 0, 0), angleDegrees=90).translate((0, 0, 1.5))
    vac_fitting_screw = SetScrew("M5-0.8", fastener_type="iso4026", length=30, simple=no_threads)  # dummy screw for making vac fitting threads

    def mkbase(
        aso: cadquery.Assembly,
        thickness: float,
        cshift,
        extents,
        hps,
        screw: SocketHeadCapScrew,
        pedistal_height: float,
        zbase: float,
        subs_boost: float,
    ):
        """the thermal base"""
        plate_name = "thermal_plate"
        vac_name = "vacuum_chuck"
        color = cadquery.Color("GOLD")
        fillet_outer = 2
        fillet_inner = 10
        chamfer = 1
        corner_screw_depth = 4.5

        pedistal_xy = (161, 152)
        pedistal_fillet = 10

        dowelpts = [(-73, -66), (73, 66)]
        dowel_nominal_d = 3  # marked on drawing for pressfit with ⌀3K7

        # vac chuck clamp screws
        vacscrew_length = 20
        vacscrew = CounterSunkScrew(size="M6-1", fastener_type="iso14581", length=vacscrew_length, simple=no_threads)  # SHK-M6-20-V2-A4
        vacclamppts = [(-73, -54.75), (-73, 54.75), (73, -54.75), (73, 54.75)]

        # slot plate clamp screws
        spscrew_length = 8
        spscrew = CounterSunkScrew(size="M3-0.5", fastener_type="iso14581", length=spscrew_length, simple=no_threads)  # SHK-M3-8-V2-A4

        # setscrew clamping stuff
        setscrew_len = 30
        screw_well_depth = 3
        setscrew_recess = pedistal_height + screw_well_depth
        setscrew = SetScrew(size="M6-1", fastener_type="iso4026", length=setscrew_len, simple=no_threads)  # SSU-M6-30-A2
        setscrewpts = [(-73, -43.5), (73, 43.5)]

        # waterblock nuts and holes
        wb_w = 177.8
        wb_mount_offset_from_edge = 7.25
        wb_mount_offset = wb_w / 2 - wb_mount_offset_from_edge
        waterblock_mount_nut = HexNutWithFlange(size="M6-1", fastener_type="din1665", simple=no_threads)  # HFFN-M6-A2
        wb_mount_points = [
            (120, wb_mount_offset),
            (120, -wb_mount_offset),
            (-129, wb_mount_offset),
            (-129, -wb_mount_offset),
        ]

        # make the base chunk
        wp = CQ().workplane(**u.copo, offset=zbase).sketch()
        wp = wp.push([cshift]).rect(extents[0], extents[1], mode="a")
        wp = wp.finalize().extrude(thickness)
        wp: cadquery.Workplane  # shouldn't have to do this (needed for type hints)

        # cut for waterblock mnt ears
        ear_square = 2 * wb_mount_offset
        wp = wp.faces("<X").workplane(**u.cobb).rect(xLen=extents[1] - 2 * ear_square, yLen=thickness, centered=True).cutBlind(-(extents[0] - wall_outer[0]) / 2)
        wp = wp.faces(">X").workplane(**u.cobb).rect(xLen=extents[1] - 2 * ear_square, yLen=thickness, centered=True).cutBlind(-(extents[0] - wall_outer[0]) / 2)
        wp = wp.edges("|Z exc (<<X or >>X)").fillet(fillet_inner)
        wp = wp.edges("|Z and (<<X or >>X)").fillet(fillet_outer)

        # pedistal
        wp = wp.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).sketch().rect(*pedistal_xy).reset().vertices().fillet(pedistal_fillet)
        wp = wp.finalize().extrude(pedistal_height)

        hardware = cq.Assembly(None)  # a place to keep the harware

        # corner screws
        wp = wp.faces("<Z").workplane(**u.copo, offset=-corner_screw_depth).pushPoints(hps).clearanceHole(fastener=screw, fit="Close", baseAssembly=hardware)
        wp = wp.faces("<Z[-2]").wires().toPending().extrude(corner_screw_depth, combine="cut")  # make sure the recessed screw is not buried

        # dowel holes
        wp = wp.faces(">Z").workplane(**u.copo).pushPoints(dowelpts).hole(dowel_nominal_d, depth=pedistal_height)

        # waterblock mounting
        wp = wp.faces(">Z[-2]").workplane(**u.copo).pushPoints(wb_mount_points).clearanceHole(fastener=waterblock_mount_nut, counterSunk=False, baseAssembly=hardware)

        # vac chuck stuff
        # split
        wp = wp.faces(">Z[-2]").workplane(**u.copo).split(keepTop=True, keepBottom=True).clean()
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

        # boost substrates up so they can't slip under
        raise_square = (25, 25)
        raise_fillet = 1
        top_piece = CQ(top_piece.findSolid()).faces(">Z").workplane(**u.copo).sketch().rarray(x_spacing, y_spacing, n_array_x, n_array_y).rect(*raise_square).reset().vertices().fillet(raise_fillet).finalize().extrude(subs_boost)

        # drill all the vac holes
        top_piece = top_piece.faces(">Z").workplane(**u.copo).pushPoints(vac_hole_pts).cskHole(diameter=hole_d, cskDiameter=hole_cskd, cskAngle=csk_ang)

        # clamping setscrew threaded holes
        wp = wp.faces(">Z").workplane().pushPoints(setscrewpts).tapHole(setscrew, depth=setscrew_recess, baseAssembly=hardware)  # bug prevents this from working correctly, workaround below
        btm_piece = CQ(btm_piece.findSolid()).faces(">Z").workplane(**u.copo).pushPoints(setscrewpts).circle(vacscrew.clearance_hole_diameters["Close"] / 2).cutBlind(-screw_well_depth)

        # vac chuck clamping screws
        top_piece = top_piece.faces(">Z[-2]").workplane(**u.copo, origin=(0, 0, 0)).pushPoints(vacclamppts).clearanceHole(vacscrew, fit="Close", baseAssembly=hardware)
        # next line is a hack to make absolutely sure the screws are recessed
        top_piece = top_piece.faces(">Z[-2]").workplane(**u.copo, origin=(0, 0, 0)).pushPoints(vacclamppts).cskHole(vacscrew.clearance_hole_diameters["Close"], cskDiameter=vacscrew.head_diameter + 1, cskAngle=vacscrew.screw_data["a"])
        btm_piece = btm_piece.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).pushPoints(vacclamppts).tapHole(vacscrew, depth=vacscrew_length - pedistal_height + 1)  # threaded holes to attach to

        # mod the slot plate to include csk screws for clamping
        for name, part in asys["squirrel"].traverse():
            if name == "slot_plate":
                sp_clamp_pts = [(p[0], p[1] + 5) for p in vacclamppts]
                sp = part.obj
                vch_shift_y = -37
                vch_shift_x = 3
                sp = sp.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).rarray(vacclamppts[3][0] * 2 + vch_shift_x, vacclamppts[3][1] * 2 + vch_shift_y, 2, 2).clearanceHole(spscrew, fit="Close", baseAssembly=hardware)
                # next line is a hack to make absolutely sure the screws are recessed
                sp = sp.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).rarray(vacclamppts[3][0] * 2 + vch_shift_x, vacclamppts[3][1] * 2 + vch_shift_y, 2, 2).cskHole(spscrew.clearance_hole_diameters["Close"], cskDiameter=spscrew.head_diameter + 1, cskAngle=spscrew.screw_data["a"])
                part.obj = sp

                # make threaded holes to attach to, TODO: mark these as M3x0.5 threaded holes in engineering drawing
                top_piece = top_piece.faces(">Z[-2]").workplane(**u.copo, origin=(0, 0, 0)).rarray(vacclamppts[3][0] * 2 + vch_shift_x, vacclamppts[3][1] * 2 + vch_shift_y, 2, 2).tapHole(spscrew, depth=spscrew_length - 1, counterSunk=False)

        # compute the hole array extents for o-ring path finding
        sub_x_length = (n_sub_array_x - 1) * x_spacing_sub + hole_d
        array_x_length = (n_array_x - 1) * x_spacing + sub_x_length

        sub_y_length = (n_sub_array_y - 1) * y_spacing_sub + hole_d
        array_y_length = (n_array_y - 1) * y_spacing + sub_y_length

        # for the vac chuck fitting
        vac_fitting_chuck_offset = -0.5 * y_spacing
        fitting_tap_depth = 20
        top_piece = top_piece.faces(">X").workplane(**u.cobb).center(vac_fitting_chuck_offset, 0).tapHole(vac_fitting_screw, depth=fitting_tap_depth)
        vac_chuck_fitting = cadquery.Assembly(a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=-5), name="chuck_vac_fitting")
        hardware.add(vac_chuck_fitting, loc=top_piece.plane.location, name="vac chuck fitting")

        # handle the valve, part number 435-8101
        a_valve = u.import_step(wrk_dir.joinpath("components", "VHK2-04F-04F.step"))
        # a_valve = a_valve.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 1, 0), angleDegrees=90).translate((0, 7.5, 9))
        a_valve = a_valve.translate((0, 7.5, 9))
        valve_mnt_spacing = 16.5
        valve_mnt_screw_length = 30
        valve_body_width = 18
        valve_mnt_hole_depth = 15
        valve_mnt_screw = PanHeadScrew(size="M4-0.7", fastener_type="iso14583", length=valve_mnt_screw_length)  # SHP-M4-30-V2-A4
        btm_piece = btm_piece.faces(">X[-2]").workplane(**u.cobb).rarray(valve_mnt_spacing, 1, 2, 1).tapHole(valve_mnt_screw, depth=valve_mnt_hole_depth, counterSunk=False)  # cut threaded holes
        btm_piece = btm_piece.faces(">X[-2]").workplane(**u.cobb).rarray(valve_mnt_spacing, 1, 2, 1).tapHole(valve_mnt_screw, depth=valve_mnt_screw_length - valve_body_width, counterSunk=False, baseAssembly=aso)  # add screws
        aso.add(a_valve, loc=btm_piece.plane.location, name="valve")

        # handle the elbow, part number 306-5993
        an_elbow = u.import_step(wrk_dir.joinpath("components", "3182_04_00.step"))
        an_elbow = an_elbow.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 1, 0), angleDegrees=-90).rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=90)  # rotate the elbow
        btm_pln = btm_piece.faces(">X[-2]").workplane(**u.cobb, offset=valve_body_width / 2).center(-26.65, 7.5)  # position the elbow
        aso.add(an_elbow, loc=btm_pln.plane.location, name="elbow")

        # vac distribution network
        zdrill_loc = (pedistal_xy[0] / 2 - fitting_tap_depth, 0.5 * y_spacing)
        zdrill_r = 3
        zdrill_depth = -pedistal_height / 2 - 2.5
        top_piece = top_piece.faces("<Z").workplane(**u.cobb).pushPoints([zdrill_loc]).circle(zdrill_r).cutBlind(zdrill_depth)

        highway_depth = 3
        highway_width = 6
        street_depth = 2
        street_width = 1
        top_piece = top_piece.faces("<Z").workplane(**u.cobb).sketch().push([(zdrill_loc[0] / 2, zdrill_loc[1])]).slot(w=zdrill_loc[0], h=highway_width).finalize().cutBlind(-highway_depth)
        top_piece = top_piece.faces("<Z").workplane(**u.cobb).sketch().slot(w=pedistal_xy[0] - 2 * fitting_tap_depth, h=highway_width, angle=90).finalize().cutBlind(-highway_depth)  # cut center highway
        top_piece = top_piece.faces("<Z").workplane(**u.cobb).sketch().push(street_centers).slot(w=array_x_length - hole_d, h=street_width).finalize().cutBlind(-street_depth)  # cut streets

        # padding to keep the oring groove from bothering the vac holes
        groove_x_pad = 8
        groove_y_pad = 16

        # that's part number 196-4941
        o_ring_thickness = 2
        o_ring_inner_diameter = 170

        # cut the o-ring groove
        top_piece = top_piece.faces("<Z").workplane(**u.cobb).mk_groove(ring_cs=o_ring_thickness, follow_pending_wires=False, ring_id=o_ring_inner_diameter, gland_x=array_x_length + groove_x_pad, gland_y=array_y_length + groove_y_pad, hardware=hardware)

        aso.add(btm_piece, name=plate_name, color=color)
        aso.add(top_piece, name=vac_name, color=color)
        aso.add(hardware.toCompound(), name="hardware", color=cadquery.Color(hardware_color))

    mkbase(asys[as_name], copper_thickness, center_shift, base_outer, corner_hole_points, corner_screw, thermal_pedestal_height, copper_base_zero, substrate_raise)

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
        inner_fillet = 6
        chamfer = 0.75

        nut = HexNut(size="M5-0.8", fastener_type="iso4033")  # HNN-M5-A2
        flat_to_flat = math.sin(60 * math.pi / 180) * nut.nut_diameter + 0.25

        gas_fitting_hole_diameter = 20.6375  # 13/16"
        gas_fitting_recess = 6.35
        gas_fitting_flat_to_flat = 22.22 + 0.28
        gas_fitting_diameter = 25.66 + 0.34

        back_holes_shift = 45
        back_holes_spacing = 27
        front_holes_spacing = 75

        wp = CQ().workplane(offset=zbase).sketch()
        wp = wp.push([cshift]).rect(extents[0], extents[1], mode="a").reset().vertices().fillet(outer_fillet)
        wp = wp.push([inner_shift]).rect(inner[0], inner[1], mode="s").reset().vertices().fillet(inner_fillet)
        wp = wp.finalize().extrude(height)
        wp: cadquery.Workplane  # shouldn't have to do this (needed for type hints)

        wall_hardware = cq.Assembly(None, name="wall_hardware")

        # corner holes (with nuts and nut pockets)
        wp = wp.faces(">Z").workplane(**u.copo, offset=-nut.nut_thickness).pushPoints(hps).clearanceHole(fastener=nut, fit="Close", counterSunk=False, baseAssembly=wall_hardware)
        wp = wp.faces(">Z").workplane(**u.copo).sketch().push(hps[0:4:3]).rect(flat_to_flat, nut.nut_diameter, angle=45).reset().push(hps[1:3]).rect(flat_to_flat, nut.nut_diameter, angle=-45).reset().vertices().fillet(nut.nut_diameter / 4).finalize().cutBlind(-nut.nut_thickness)

        # chamfers
        wp = wp.faces(">Z").edges(">>X").chamfer(chamfer)

        # gas holes with recesses
        wp = wp.faces("<X").workplane(**u.cobb).center(back_holes_shift, 0).rarray(back_holes_spacing, 1, 2, 1).hole(diameter=gas_fitting_hole_diameter, depth=thickness)
        # wp = wp.faces("<X").workplane(**u.cobb).center(back_holes_shift, 0).sketch().rarray(back_holes_spacing, 1, 2, 1).rect(gas_fitting_diameter, gas_fitting_flat_to_flat).reset().vertices().fillet(gas_fitting_diameter / 4).finalize().cutBlind(-gas_fitting_recess)
        wp = wp.faces("<X").workplane(**u.cobb).center(back_holes_shift, 0).sketch().rect(2 * gas_fitting_diameter / 2 + back_holes_spacing, gas_fitting_flat_to_flat).reset().vertices().fillet(gas_fitting_diameter / 4).finalize().cutBlind(-gas_fitting_recess)  # unify the back holes
        wp = wp.faces(">X").workplane(**u.cobb).rarray(front_holes_spacing, 1, 2, 1).hole(diameter=gas_fitting_hole_diameter, depth=thickness)
        wp = wp.faces(">X").workplane(**u.cobb).sketch().rarray(front_holes_spacing, 1, 2, 1).rect(gas_fitting_diameter, gas_fitting_flat_to_flat).reset().vertices().fillet(gas_fitting_diameter / 4).finalize().cutBlind(-gas_fitting_recess)

        # that's part number polymax 230X2N70
        o_ring_thickness = 2
        o_ring_inner_diameter = 230
        ooffset = 17  # two times the o-ring path's center offset from the outer edge of the walls

        # cut the lid o-ring groove
        wp = wp.faces(">Z").workplane(**u.cobb).mk_groove(ring_cs=o_ring_thickness, follow_pending_wires=False, ring_id=o_ring_inner_diameter, gland_x=extents[0] - ooffset, gland_y=extents[1] - ooffset, hardware=wall_hardware)

        # cut the base o-ring groove
        wp = wp.faces("<Z").workplane(**u.cobb).mk_groove(ring_cs=o_ring_thickness, follow_pending_wires=False, ring_id=o_ring_inner_diameter, gland_x=extents[0] - ooffset, gland_y=extents[1] - ooffset, hardware=wall_hardware)

        # get pipe fitting geometry
        a_pipe_fitting = u.import_step(wrk_dir.joinpath("components", "5483T93_Miniature Nickel-Plated Brass Pipe Fitting.step"))
        a_pipe_fitting = a_pipe_fitting.translate((0, 0, -6.35 - gas_fitting_recess))
        pipe_fitting_asy = cadquery.Assembly(a_pipe_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=30), name="one_pipe_fitting")

        # move the pipe fittings to their wall holes
        wppf = wp.faces(">X").workplane(**u.cobb).center(front_holes_spacing / 2, 0)
        pipe_fitting_asy.loc = wppf.plane.location
        wall_hardware.add(pipe_fitting_asy, name="front_right_gas_fitting")
        wppf = wppf.center(-front_holes_spacing, 0)
        pipe_fitting_asy.loc = wppf.plane.location
        wall_hardware.add(pipe_fitting_asy, name="front_left_gas_fitting")
        wppf = wp.faces("<X").workplane(**u.cobb).center(back_holes_shift + back_holes_spacing / 2, 0)
        pipe_fitting_asy.loc = wppf.plane.location
        wall_hardware.add(pipe_fitting_asy, name="rear_left_gas_fitting")
        wppf = wppf.center(-back_holes_spacing, 0)
        pipe_fitting_asy.loc = wppf.plane.location
        wall_hardware.add(pipe_fitting_asy, name="rear_right_gas_fitting")

        # get bonded washer geometry, part 229-6277
        bonded_washer = u.import_step(wrk_dir.joinpath("components", "hutchinson_ljf_207242.stp"))
        bonded_washer = bonded_washer.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 1, 0), angleDegrees=90).translate((0, 0, 1.25))
        bonded_washer_asy = cadquery.Assembly(bonded_washer, name="one_bonded_washer")

        # move bonded washers to their wall holes
        wpbw = wp.faces(">X[-5]").workplane(**u.cobb).center(-front_holes_spacing / 2, 0)
        bonded_washer_asy.loc = wpbw.plane.location
        wall_hardware.add(bonded_washer_asy, name="front_right_bonded_washer")
        wpbw = wpbw.center(front_holes_spacing, 0)
        bonded_washer_asy.loc = wpbw.plane.location
        wall_hardware.add(bonded_washer_asy, name="front_left_bonded_washer")
        wpbw = wp.faces("<X[-5]").workplane(**u.cobb).center(-back_holes_shift - back_holes_spacing / 2, 0)
        bonded_washer_asy.loc = wpbw.plane.location
        wall_hardware.add(bonded_washer_asy, name="rear_right_bonded_washer")
        wpbw = wpbw.center(back_holes_spacing, 0)
        bonded_washer_asy.loc = wpbw.plane.location
        wall_hardware.add(bonded_washer_asy, name="rear_left_bonded_washer")

        aso.add(wall_hardware.toCompound(), name="wall_hardware", color=cadquery.Color(hardware_color))

        # passthrough details
        pcb_scr_head_d_safe = 6
        n_header_pins = 50
        header_length = n_header_pins / 2 * 2.54 + 7.62  # n*0.1 + 0.3 inches
        support_block_width = 7
        pt_pcb_width = 2 * (support_block_width / 2 + pcb_scr_head_d_safe / 2) + header_length
        pt_pcb_outer_depth = 8.89 + 0.381  # 0.35 + 0.15 inches
        pt_pcb_inner_depth = 8.89 + 0.381  # 0.35 + 0.15 inches
        pt_center_offset = 28.65  # so that the internal passthrough connector aligns with the one in the chamber

        # make the electrical passthrough
        pt_asy = cadquery.Assembly()  # this will hold the passthrough part that gets created
        # pcb_asy = cadquery.Assembly()  # this will hold the pcb part that gets created
        pcb_asy = None  # dont generate the base PCB (will probably later import the detailed board model)
        hw_asy = cadquery.Assembly()  # this will hold the pcb part that gets created
        ptt = 5.5  # passthrough thickness, reduce a bit from default (which was half wall thickness) to prevent some thin walls close to an o-ring gland
        wp = wp.faces("<X").workplane(**u.cobb).center(-pt_center_offset, 0).make_oringer(board_width=pt_pcb_width, board_inner_depth=pt_pcb_inner_depth, board_outer_depth=pt_pcb_outer_depth, wall_depth=thickness, part_thickness=ptt, pt_asy=pt_asy, pcb_asy=pcb_asy, hw_asy=hw_asy)
        # insert passthrough into assembly
        for asyo in pt_asy.traverse():
            part = asyo[1]
            if isinstance(part.obj, cadquery.occ_impl.shapes.Solid):
                aso.add(part.obj, name=asyo[0], color=color)
        if pcb_asy is not None:
            # insert pcb into assembly
            for asyo in pcb_asy.traverse():  # insert only one solid object
                part = asyo[1]
                if isinstance(part.obj, cadquery.occ_impl.shapes.Solid):
                    aso.add(part.obj, name=asyo[0], color=cadquery.Color("DARKGREEN"))
        # insert hardware into assembly
        aso.add(hw_asy.toCompound(), name="passthrough hardware")

        # add in little detailed PCB
        a_little_pcb = u.import_step(wrk_dir.joinpath("components", "pt_pcb.step"))
        little_pcb = cadquery.Assembly(a_little_pcb.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 1, 0), angleDegrees=90), name="small detailed pcb")
        asys["squirrel"].add(little_pcb, loc=wp.plane.location, name="little pcb")

        # for the vac chuck fittings
        rotation_angle = -155  # degrees
        vac_fitting_wall_offset = extents[1] / 2 - thickness - inner_fillet - 4  # mounting location offset from center
        wp = wp.faces(">X").workplane(**u.cobb).center(vac_fitting_wall_offset, 0).tapHole(vac_fitting_screw, depth=thickness)
        vac_chuck_fitting = cadquery.Assembly(a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=rotation_angle), name="outer_wall_vac_fitting")
        aso.add(vac_chuck_fitting, loc=wp.plane.location, name="vac chuck fitting (wall outer)")

        nwp = wp.faces(">X").workplane(**u.cobb, invert=True, offset=thickness).center(vac_fitting_wall_offset, 0)
        vac_chuck_fitting = cadquery.Assembly(a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=-rotation_angle), name="inner_wall_vac_fitting")
        aso.add(vac_chuck_fitting, loc=nwp.plane.location, name="vac chuck fitting (wall inner)")

        aso.add(wp, name=name, color=color)  # add the walls bulk

    mkwalls(asys[as_name], wall_height, center_shift, wall_outer, corner_hole_points, copper_base_zero + copper_thickness)

    # add in big detailed PCB
    big_pcb = u.import_step(wrk_dir.joinpath("components", "pcb.step"))
    asys["squirrel"].add(big_pcb, name="big pcb")

    TwoDToThreeD.outputter(asys, wrk_dir)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
