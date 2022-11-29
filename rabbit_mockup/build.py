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

# fitting notes:
# quantity 2 of RS Stock No.:176-1299
#


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
    substrate_thickness = 1.1
    copper_thickness = 10
    thermal_pedestal_height = 14.1
    slot_plate_thickness = 2.3 + substrate_raise
    pcb_thickness = 1.6
    pusher_thickness = 4
    dowel_length = slot_plate_thickness + pcb_thickness + pusher_thickness + thermal_pedestal_height + 3  # nominally 25
    wall_height = 32
    sleeve_holder_thickness = 15.25 - pcb_thickness
    passthrough_standoff_height = 15
    pin_travel = 2.65
    no_substrate_pin_compression = 0.2
    hardware_color = "GRAY75"
    pcb_standoff_height = 5
    pcb_base_offset = 5
    underpocket_airgap = pcb_base_offset + pcb_thickness + pcb_standoff_height
    pin_sleeve_end_to_stopper_len = 17.75 - 2.5
    pin_stopper_drilldown = pcb_base_offset + pin_sleeve_end_to_stopper_len
    pocket_depth_drilldown = pin_stopper_drilldown + 2.5 + 2.65 * 2 / 3
    tower_thermal_pad_thickness = 0.5
    tower_height = pocket_depth_drilldown - tower_thermal_pad_thickness

    # for 3m6 dowel pins (3m6 ones are +2um to +8um larger than the nominal 3mm diameter)
    dowel3_delta_press = -0.005  # draw pressfit holes as 5um smaller than nominal, mark as 3K7 (-0um to -10um allowed)
    dowel3_delta_slide = 0.1  # draw slidefit holes as 100um larger than nominal, mark as 3C11 (+60um to +120um allowed)

    # base posision of the pedistal now
    copper_base_zero = -copper_thickness

    as_name = "rabbit"
    instructions.append(
        {
            "name": as_name,
            "layers": [
                # {
                #     "name": "pusher",
                #     "color": "GREEN",
                #     "thickness": pusher_thickness,
                #     "z_base": 6.2 + pcb_thickness + sleeve_holder_thickness + pin_travel - no_substrate_pin_compression,
                #     "drawing_layer_names": [
                #         "pusher_outer",
                #         "pusher_inner_small",
                #     ],
                # },
                {
                    "name": "substrates",
                    "color": "BLUE",
                    "thickness": substrate_thickness,
                    "z_base": pocket_depth_drilldown,
                    "drawing_layer_names": [
                        "small_glasses",
                    ],
                },
                # {
                #     "name": "slot_plate",
                #     "color": "RED",
                #     "thickness": slot_plate_thickness,
                #     "z_base": 6.2 + pcb_thickness + sleeve_holder_thickness + pin_travel - no_substrate_pin_compression - slot_plate_thickness,
                #     "drawing_layer_names": [
                #         "slot_plate_outer",
                #         "slot_plate_inner_small",
                #     ],
                # },
                {
                    "name": "pcb",
                    "color": "DARKGREEN",
                    "thickness": pcb_thickness,
                    "z_base": pcb_base_offset,
                    "drawing_layer_names": [
                        "pcb",
                    ],
                },
            ],
        }
    )

    ttt = TwoDToThreeD(instructions=instructions, sources=sources)
    to_build = [""]
    asys = ttt.build(to_build)

    no_threads = True  # set true to make all the hardware have no threads (much faster, smaller)
    center_shift = (0, 0)
    wall_outer = (119, 119)
    corner_holes_offset = 7.5
    corner_hole_points = [(x * (wall_outer[0] - 2 * corner_holes_offset) - (wall_outer[0] - 2 * corner_holes_offset) / 2 + center_shift[0], y * (wall_outer[1] - 2 * corner_holes_offset) - (wall_outer[1] - 2 * corner_holes_offset) / 2 + center_shift[1]) for x, y in itertools.product(range(0, 2), range(0, 2))]
    assembly_screw_length = 45
    corner_screw = CheeseHeadScrew(size="M5-0.8", fastener_type="iso14580", length=assembly_screw_length, simple=no_threads)  # SHC-M5-45-A2

    # base_outer = (wall_outer[0] + 40, wall_outer[1])

    outer_fillet = 2

    # # get vac fitting geometry
    # # takes 4mm OD tubes, needs M5x0.8 threads, part number 326-8956
    # a_vac_fitting = u.import_step(wrk_dir.joinpath("components", "3118_04_19.step"))
    # a_vac_fitting = a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(1, 0, 0), angleDegrees=90).translate((0, 0, 1.5))
    # vac_fitting_screw = SetScrew("M5-0.8", fastener_type="iso4026", length=30, simple=no_threads)  # dummy screw for making vac fitting threads

    def mkbase(
        wrk_dir: Path,
        aso: cadquery.Assembly,
        thickness: float,
        cshift,
        wall_extents,
        hps,
        screw: SocketHeadCapScrew,
        pedistal_height: float,
        zbase: float,
        subs_boost: float,
        outer_fillet: float,
    ):
        """the thermal base"""
        enable_towers = True
        if enable_towers:
            plate_name = "thermal_towers_base_plate"
        else:
            plate_name = "no_towers_base_plate"
        # vac_name = "vacuum_chuck"
        color = cadquery.Color("GOLD")
        fillet_inner = 10
        chamfer = 1
        corner_screw_depth = 3

        # pedistal_xy = (161, 152)
        # pedistal_fillet = 10

        # dowelpts = [(-73, -66), (73, 66)]
        # dowel_nominal_d = 3  # marked on drawing for pressfit with ⌀3K7

        # # vac chuck clamp screws
        # vacscrew_length = 20
        # vacscrew = CounterSunkScrew(size="M6-1", fastener_type="iso14581", length=vacscrew_length, simple=no_threads)  # SHK-M6-20-V2-A4
        # vacclamppts = [(-73, -54.75), (-73, 54.75), (73, -54.75), (73, 54.75)]

        # slot plate clamp screws
        spscrew_length = 8
        spscrew = CounterSunkScrew(size="M3-0.5", fastener_type="iso14581", length=spscrew_length, simple=no_threads)  # SHK-M3-8-V2-A4

        # setscrew clamping stuff
        # setscrew_len = 30
        # screw_well_depth = 3
        # setscrew_recess = pedistal_height + screw_well_depth
        # setscrew = SetScrew(size="M6-1", fastener_type="iso4026", length=setscrew_len, simple=no_threads)  # SSU-M6-30-A2
        # setscrewpts = [(-73, -43.5), (73, 43.5)]

        # waterblock nuts and holes
        wb_mount_offset_from_edge = 7.25
        # extension_for_cooler = 2*36
        extension_for_cooler = 0
        wb_y = wall_extents[1]
        wb_mount_offset_y = wb_y / 2 - wb_mount_offset_from_edge
        wb_x = wall_extents[0] + wb_mount_offset_from_edge * 4 + extension_for_cooler
        wb_mount_offset_x = wb_x / 2 - wb_mount_offset_from_edge
        waterblock_mount_nut = HexNutWithFlange(size="M6-1", fastener_type="din1665", simple=no_threads)  # HFFN-M6-A2
        wb_mount_points = [
            (wb_mount_offset_x, wb_mount_offset_y),
            (wb_mount_offset_x, -wb_mount_offset_y),
            (-wb_mount_offset_x, wb_mount_offset_y),
            (-wb_mount_offset_x, -wb_mount_offset_y),
        ]

        # make the base chunk
        wp = CQ().workplane(**u.copo, offset=zbase).sketch()
        wp = wp.push([cshift]).rect(wb_x, wb_y, mode="a")
        wp = wp.finalize().extrude(thickness)
        wp: cadquery.Workplane  # shouldn't have to do this (needed for type hints)

        ear_square = 2 * wb_mount_offset_from_edge
        if enable_towers:
            # cut for waterblock mnt ears
            wp = wp.faces("-X").workplane(**u.cobb).rect(xLen=wb_y - 2 * ear_square, yLen=thickness, centered=True).cutBlind(-ear_square)
            wp = wp.faces("+X").workplane(**u.cobb).rect(xLen=wb_y - 2 * ear_square, yLen=thickness, centered=True).cutBlind(-ear_square)
            wp = wp.edges("|Z exc (<<X or >>X)").fillet(fillet_inner)
        else:
            wp = wp.faces("-X").workplane(**u.cobb).rect(xLen=wb_y, yLen=thickness, centered=True).cutBlind(-ear_square)
            wp = wp.faces("+X").workplane(**u.cobb).rect(xLen=wb_y, yLen=thickness, centered=True).cutBlind(-ear_square)

        wp = wp.edges("|Z and (<<X or >>X)").fillet(outer_fillet)

        # pedistal
        # wp = wp.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).sketch().rect(*pedistal_xy).reset().vertices().fillet(pedistal_fillet)
        # wp = wp.finalize().extrude(pedistal_height)

        hardware = cq.Assembly(None)  # a place to keep the harware

        # corner screws
        # wp = wp.faces("-Z").workplane(**u.cobb).circle(3).extrude(1)
        wp = wp.faces("<Z").workplane(**u.cobb, offset=-corner_screw_depth).pushPoints(hps).clearanceHole(fastener=screw, fit="Close", baseAssembly=hardware)
        wp = wp.faces("<Z[-2]").wires().toPending().extrude(corner_screw_depth, combine="cut")  # make sure the recessed screw is not buried

        # dowel holes
        # wp = wp.faces(">Z").workplane(**u.copo).pushPoints(dowelpts).hole(dowel_nominal_d + dowel3_delta_press, depth=pedistal_height)

        # waterblock mounting
        if enable_towers:
            wp = wp.faces(">Z").workplane(**u.copo).pushPoints(wb_mount_points).clearanceHole(fastener=waterblock_mount_nut, counterSunk=False, fit="Loose", baseAssembly=hardware)

        # vac chuck stuff
        # split
        # wp = wp.faces(">Z[-2]").workplane(**u.copo).split(keepTop=True, keepBottom=True).clean()
        # btm_piece = wp.solids("<Z").first().edges("not %CIRCLE").chamfer(chamfer)
        # top_piece = wp.solids(">Z").first().edges("not %CIRCLE").chamfer(chamfer)

        # # hole array
        # n_array_x = 4
        # n_array_y = 5
        # x_spacing = 35
        # y_spacing = 29
        # x_start = (n_array_x - 1) / 2
        # y_start = (n_array_y - 1) / 2

        # n_sub_array_x = 8
        # n_sub_array_y = 2
        # x_spacing_sub = 3
        # y_spacing_sub = 10
        # x_start_sub = (n_sub_array_x - 1) / 2
        # y_start_sub = (n_sub_array_y - 1) / 2

        # hole_d = 1
        # hole_cskd = 1.1
        # csk_ang = 45

        # # compute all the vac chuck vent hole points
        # vac_hole_pts = []  # where the vac holes are drilled
        # street_centers = []  # the distribution street y values
        # for i in range(n_array_x):
        #     for j in range(n_array_y):
        #         for k in range(n_sub_array_x):
        #             for l in range(n_sub_array_y):
        #                 ctrx = (i - x_start) * x_spacing
        #                 ctry = (j - y_start) * y_spacing
        #                 offx = (k - x_start_sub) * x_spacing_sub
        #                 offy = (l - y_start_sub) * y_spacing_sub
        #                 vac_hole_pts.append((ctrx + offx, ctry + offy))
        #                 street_centers.append((0, ctry + offy))
        # street_centers = list(set(street_centers))  # prune duplicates

        # # boost substrates up so they can't slip under
        # raise_square = (25, 25)
        # raise_fillet = 1
        # top_piece = CQ(top_piece.findSolid()).faces(">Z").workplane(**u.copo).sketch().rarray(x_spacing, y_spacing, n_array_x, n_array_y).rect(*raise_square).reset().vertices().fillet(raise_fillet).finalize().extrude(subs_boost)

        # # drill all the vac holes
        # top_piece = top_piece.faces(">Z").workplane(**u.copo).pushPoints(vac_hole_pts).cskHole(diameter=hole_d, cskDiameter=hole_cskd, cskAngle=csk_ang)

        # # clamping setscrew threaded holes
        # top_piece = top_piece.faces(">Z").workplane().pushPoints(setscrewpts).tapHole(setscrew, depth=setscrew_recess, baseAssembly=hardware)  # bug prevents this from working correctly, workaround below
        # # clamping setscrew downbumps in the thermal plate
        # btm_piece = CQ(btm_piece.findSolid()).faces(">Z").workplane(**u.copo).pushPoints(setscrewpts).circle(vacscrew.clearance_hole_diameters["Close"] / 2).cutBlind(-screw_well_depth)

        # # vac chuck clamping screws
        # top_piece = top_piece.faces(">Z[-2]").workplane(**u.copo, origin=(0, 0, 0)).pushPoints(vacclamppts).clearanceHole(vacscrew, fit="Close", baseAssembly=hardware)
        # # next line is a hack to make absolutely sure the screws are recessed
        # top_piece = top_piece.faces(">Z[-2]").workplane(**u.copo, origin=(0, 0, 0)).pushPoints(vacclamppts).cskHole(vacscrew.clearance_hole_diameters["Close"], cskDiameter=vacscrew.head_diameter + 1, cskAngle=vacscrew.screw_data["a"])
        # btm_piece = btm_piece.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).pushPoints(vacclamppts).tapHole(setscrew, depth=vacscrew_length - pedistal_height + 1)  # threaded holes to attach to

        # # mod the slot plate to include csk screws for clamping
        # for name, part in asys["squirrel"].traverse():
        #     if name == "slot_plate":
        #         sp_clamp_pts = [(p[0], p[1] + 5) for p in vacclamppts]
        #         sp = cq.Workplane().add(part.shapes)
        #         vch_shift_y = -37
        #         vch_shift_x = 3
        #         sp = sp.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).rarray(vacclamppts[3][0] * 2 + vch_shift_x, vacclamppts[3][1] * 2 + vch_shift_y, 2, 2).clearanceHole(spscrew, fit="Close", baseAssembly=hardware)
        #         # next line is a hack to make absolutely sure the screws are recessed
        #         sp = sp.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).rarray(vacclamppts[3][0] * 2 + vch_shift_x, vacclamppts[3][1] * 2 + vch_shift_y, 2, 2).cskHole(spscrew.clearance_hole_diameters["Close"], cskDiameter=spscrew.head_diameter + 1, cskAngle=spscrew.screw_data["a"])
        #         part.obj = sp

        #         # make threaded holes to attach to, TODO: mark these as M3x0.5 threaded holes in engineering drawing
        #         top_piece = top_piece.faces(">Z[-2]").workplane(**u.copo, origin=(0, 0, 0)).rarray(vacclamppts[3][0] * 2 + vch_shift_x, vacclamppts[3][1] * 2 + vch_shift_y, 2, 2).tapHole(spscrew, depth=spscrew_length - 1, counterSunk=False)

        # # compute the hole array extents for o-ring path finding
        # sub_x_length = (n_sub_array_x - 1) * x_spacing_sub + hole_d
        # array_x_length = (n_array_x - 1) * x_spacing + sub_x_length

        # sub_y_length = (n_sub_array_y - 1) * y_spacing_sub + hole_d
        # array_y_length = (n_array_y - 1) * y_spacing + sub_y_length

        # # for the vac chuck fitting
        # vac_fitting_chuck_offset = -0.5 * y_spacing
        # fitting_tap_depth = 20
        # top_piece = top_piece.faces(">X").workplane(**u.cobb).center(vac_fitting_chuck_offset, 0).tapHole(vac_fitting_screw, depth=fitting_tap_depth)
        # vac_chuck_fitting = cadquery.Assembly(a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=-5), name="chuck_vac_fitting")
        # hardware.add(vac_chuck_fitting, loc=top_piece.plane.location, name="vac chuck fitting")

        # # handle the valve, part number 435-8101
        # a_valve = u.import_step(wrk_dir.joinpath("components", "VHK2-04F-04F.step"))
        # # a_valve = a_valve.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 1, 0), angleDegrees=90).translate((0, 7.5, 9))
        # a_valve = a_valve.translate((0, 7.5, 9))
        # valve_mnt_spacing = 16.5
        # valve_mnt_screw_length = 30
        # valve_body_width = 18
        # valve_mnt_hole_depth = 15
        # valve_mnt_screw = PanHeadScrew(size="M4-0.7", fastener_type="iso14583", length=valve_mnt_screw_length)  # SHP-M4-30-V2-A4
        # btm_piece = btm_piece.faces(">X[-2]").workplane(**u.cobb).rarray(valve_mnt_spacing, 1, 2, 1).tapHole(valve_mnt_screw, depth=valve_mnt_hole_depth, counterSunk=False)  # cut threaded holes
        # btm_piece = btm_piece.faces(">X[-2]").workplane(**u.cobb).rarray(valve_mnt_spacing, 1, 2, 1).tapHole(valve_mnt_screw, depth=valve_mnt_screw_length - valve_body_width, counterSunk=False, baseAssembly=aso)  # add screws
        # aso.add(a_valve, loc=btm_piece.plane.location, name="valve")

        # # handle the elbow, part number 306-5993
        # an_elbow = u.import_step(wrk_dir.joinpath("components", "3182_04_00.step"))
        # an_elbow = an_elbow.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 1, 0), angleDegrees=-90).rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=90)  # rotate the elbow
        # btm_pln = btm_piece.faces(">X[-2]").workplane(**u.cobb, offset=valve_body_width / 2).center(-26.65, 7.5)  # position the elbow
        # aso.add(an_elbow, loc=btm_pln.plane.location, name="elbow")

        # # vac distribution network
        # zdrill_loc = (pedistal_xy[0] / 2 - fitting_tap_depth, 0.5 * y_spacing)
        # zdrill_r = 3
        # zdrill_depth = -pedistal_height / 2 - 2.5
        # top_piece = top_piece.faces("<Z").workplane(**u.cobb).pushPoints([zdrill_loc]).circle(zdrill_r).cutBlind(zdrill_depth)

        # highway_depth = 3
        # highway_width = 6
        # street_depth = 2
        # street_width = 1
        # top_piece = top_piece.faces("<Z").workplane(**u.cobb).sketch().push([(zdrill_loc[0] / 2, zdrill_loc[1])]).slot(w=zdrill_loc[0], h=highway_width).finalize().cutBlind(-highway_depth)
        # top_piece = top_piece.faces("<Z").workplane(**u.cobb).sketch().slot(w=pedistal_xy[0] - 2 * fitting_tap_depth, h=highway_width, angle=90).finalize().cutBlind(-highway_depth)  # cut center highway
        # top_piece = top_piece.faces("<Z").workplane(**u.cobb).sketch().push(street_centers).slot(w=array_x_length - hole_d, h=street_width).finalize().cutBlind(-street_depth)  # cut streets

        # # padding to keep the oring groove from bothering the vac holes
        # groove_x_pad = 8
        # groove_y_pad = 16

        # # that's part number 196-4941
        # o_ring_thickness = 2
        # o_ring_inner_diameter = 170

        # # cut the o-ring groove
        # top_piece = top_piece.faces("<Z").workplane(**u.cobb).mk_groove(ring_cs=o_ring_thickness, follow_pending_wires=False, ring_id=o_ring_inner_diameter, gland_x=array_x_length + groove_x_pad, gland_y=array_y_length + groove_y_pad, hardware=hardware)

        # # cut the electrical contact screw mount holes
        # vc_e_screw_spacing = 15
        # vc_e_screw_center_offset = 10
        # vc_e_screw_hole_depth = 12
        # vc_e_screw_screw_length = 8
        # vc_e_srew_type = "M3-0.5"
        # e_dummy = SetScrew(vc_e_srew_type, fastener_type="iso4026", length=vc_e_screw_screw_length, simple=no_threads)

        # # mark these chuck electrical connection screw holes in engineering drawing as M3x0.5
        # top_piece = top_piece.faces("<X").workplane(**u.cobb).center(vc_e_screw_center_offset, 0).rarray(vc_e_screw_spacing, 1, 2, 1).tapHole(e_dummy, depth=vc_e_screw_hole_depth)

        # # the towers
        # wp7 = CQ().workplane(offset=-5).sketch()
        # wp7 = wp7.push([cshift]).rect(extents[0], extents[1], mode="a").reset().vertices().fillet(outer_fillet)
        # wp7_base = wp7.finalize().extrude(5)

        wp = wp.faces(">Z").edges("not %CIRCLE").chamfer(chamfer)
        wp = wp.faces("<Z").edges("not %CIRCLE").chamfer(chamfer)

        if enable_towers:
            # extrude towers
            twrs = cadquery.importers.importDXF(str(wrk_dir / "drawings" / "2d.dxf"), include=["towers"]).wires().toPending().extrude(tower_height)

            # make tmp measurement widget mounting
            widget_mount_hole_d = 2.3
            widget_length = 4.83
            tower_square = 7
            offset_from_top = widget_mount_hole_d / 2 + 0.5
            depth = tower_square / 2 + widget_length / 2
            wire_channel_depth = 1.5
            wire_channel_length = 20
            # cut the mounting hole
            twrs = twrs.faces("+Y").faces(">X").faces(">Y").workplane(**u.cobb).center(0, tower_height / 2 - offset_from_top).circle(widget_mount_hole_d / 2).cutBlind(-depth)
            # cut the wire slot
            twrs = twrs.faces("+Y").faces(">X").faces(">Y").workplane(**u.cobb).center(0, tower_height / 2 - offset_from_top - wire_channel_length / 2).slot2D(wire_channel_length + widget_mount_hole_d, widget_mount_hole_d, angle=90).cutBlind(-wire_channel_depth)

            wp = wp.union(twrs)

        # aso.add(twr_part, name="towers", color=cadquery.Color("goldenrod"))  # add the towers bulk

        aso.add(wp, name=plate_name, color=color)
        # aso.add(top_piece, name=vac_name, color=color)
        aso.add(hardware.toCompound(), name="hardware", color=cadquery.Color(hardware_color))

    mkbase(wrk_dir, asys[as_name], copper_thickness, center_shift, wall_outer, corner_hole_points, corner_screw, thermal_pedestal_height, copper_base_zero, substrate_raise, outer_fillet)

    def mkwalls(
        wrk_dir: Path,
        aso: cadquery.Assembly,
        height: float,
        cshift,
        extents,
        hps,
        zbase: float,
        outer_fillet: float,
    ):
        """the chamber walls"""
        name = "walls"
        color = cadquery.Color("GRAY55")
        thickness = 17
        inner = (extents[0] - 2 * thickness, extents[1] - 2 * thickness)
        inner_shift = cshift
        inner_fillet = 6
        chamfer = 0.75

        nut = HexNut(size="M5-0.8", fastener_type="iso4033")  # HNN-M5-A2
        flat_to_flat = math.sin(60 * math.pi / 180) * nut.nut_diameter + 0.25

        # gas_fitting_hole_diameter = 20.6375  # 13/16"
        # gas_fitting_recess = 6.35
        # gas_fitting_flat_to_flat = 22.22 + 0.28
        # gas_fitting_diameter = 25.66 + 0.34

        # back_holes_shift = 45
        # back_holes_spacing = 27
        # front_holes_spacing = 75

        fitting_step_xy = (3, 15)  # dims of the little step for the vac fitting alignment
        fitting_step_center = (-fitting_step_xy[0] / 2 + inner[0] / 2 + cshift[0], extents[1] / 2 - fitting_step_xy[1] / 2 - thickness)
        wp = CQ().workplane(offset=zbase).sketch()
        wp = wp.push([cshift]).rect(extents[0], extents[1], mode="a").reset().vertices().fillet(outer_fillet)
        # wp = wp.push([inner_shift]).rect(inner[0], inner[1], mode="s").reset()
        # dummy_xy = (fitting_step_xy[0], inner[1])
        # dummy_center = (fitting_step_center[0], 0)
        # wp = wp.push([dummy_center]).rect(*dummy_xy, mode="a")  # add on a dummy bit that we'll mostly subtract away

        wp = wp.finalize().extrude(height)

        # underpocket
        up = CQ().workplane(offset=zbase).sketch()
        up = up.push([inner_shift]).rect(inner[0], inner[1], mode="a").reset()
        up = up.finalize().extrude(underpocket_airgap)
        wp = wp.cut(up)

        # overpocket
        overpocket_airgap = 1 + 2.48
        wp = wp.faces(">Z").workplane(**u.cobb).sketch()
        wp = wp.push([inner_shift]).rect(inner[0], inner[1], mode="a").reset()
        wp = wp.finalize().cutBlind(-overpocket_airgap)

        # wp9 = CQ().workplane(offset=zbase).sketch()
        # wp9 = wp9.push([inner_shift]).rect(inner[0], inner[1], mode="a").reset()
        # wp9 = wp9.finalize().extrude(height).translate((0, 0, 6.2 + 15.25))
        # wp = wp.cut(wp9)

        # fillet the under/overpocket edges
        wp = wp.edges("|Z").fillet(inner_fillet)

        # cut thru_stuff
        # layers_to_cut = ["small_tower_holes", "small_pin_holes_force"]
        layers_to_cut = ["small_tower_holes", "small_pin_holes_force", "small_pin_holes_sense"]
        cut_thru = cadquery.importers.importDXF(str(wrk_dir / "drawings" / "2d.dxf"), include=layers_to_cut).wires().toPending().extrude(height)
        wp = wp.cut(cut_thru)

        # # the fitting bump
        # sub_xy = (40, inner[1] - fitting_step_xy[1])
        # sub_center = (-sub_xy[0] / 2 + inner[0] / 2 + cshift[0], -fitting_step_xy[1] / 2)
        # wp2 = CQ().workplane(offset=zbase).sketch().push([sub_center]).rect(*sub_xy, mode="a")
        # wp2 = wp2.finalize().extrude(height).edges("|Z").fillet(inner_fillet)
        # wp = wp.cut(wp2)

        # wp = CQ().workplane(offset=zbase).sketch()
        # wp = wp.push([cshift]).rect(extents[0], extents[1], mode="a").reset().vertices().fillet(outer_fillet)
        # wp = wp.push([inner_shift]).rect(inner[0], inner[1], mode="s")  # .reset().vertices().fillet(inner_fillet)
        # wp = wp.finalize().extrude(height)
        wp: cadquery.Workplane  # shouldn't have to do this (needed for type hints)

        wall_hardware = cq.Assembly(None, name="wall_hardware")

        # cut the top gas hole
        gas_hole_diameter = 4.2
        # side_depth = extents[0] / 2 - 10
        side_depth = 40
        top_cyl_length = 36
        wp = wp.faces("<X").workplane(**u.cobb).circle(gas_hole_diameter / 2).cutBlind(-side_depth)

        # cut the angle gas hole
        # cyl = wp.faces(">Z[-2]").workplane(**u.cobb).transformed(rotate=cq.Vector(0, 45, 0)).cylinder(height=top_cyl_length, radius=gas_hole_diameter / 2, centered=(True, True, True), combine=False)
        # wp = wp.cut(cyl)

        # pusher-downer secureer
        wp = wp.faces(">Z[-2]").workplane(**u.cobb, offset=-nut.nut_thickness * 2).pushPoints([(0, 35), (0, -35)]).clearanceHole(fastener=nut, fit="Close", counterSunk=False, baseAssembly=wall_hardware)
        wp = wp.faces(">Z[-2]").workplane(**u.cobb).sketch().push([(0, 35), (0, -35)]).rect(flat_to_flat, nut.nut_diameter, angle=90).reset().vertices().fillet(nut.nut_diameter / 4).finalize().cutBlind(-nut.nut_thickness * 2)

        wp = wp.faces("<Z[-2]").workplane(**u.cobb).pushPoints([(0, 35), (0, -35)]).clearanceHole(fastener=corner_screw, fit="Close", baseAssembly=wall_hardware, counterSunk=False)
        # wp = wp.faces("<Z[-2]").wires().toPending().extrude(corner_screw_depth, combine="cut")  # make sure the recessed screw is not buried

        # cut the bottom gas hole and the vent holes
        vent_hole_spacing = 35
        gas_hole_diameter = 4.2
        # side_depth = extents[0] / 2 + 4
        side_depth = 40
        side_vent_depth = 25
        top_cyl_length = 18
        wp = wp.faces(">X").workplane(**u.cobb).circle(gas_hole_diameter / 2).cutBlind(-side_depth)
        wp = wp.faces(">X").workplane(**u.cobb).rarray(vent_hole_spacing * 2, 1, 2, 1).circle(gas_hole_diameter / 2).cutBlind(-side_vent_depth)
        # cut the angle gas hole
        # cyl = wp.faces("<Z[-2]").workplane(**u.cobb).transformed(rotate=cq.Vector(0, -45, 0)).cylinder(height=top_cyl_length, radius=gas_hole_diameter / 2, centered=(True, True, True), combine=False)
        # wp = wp.cut(cyl)
        wp = wp.faces("<Z[-2]").workplane(**u.cobb).center(x=vent_hole_spacing, y=0).rarray(1, 2 * vent_hole_spacing, 1, 2).circle(gas_hole_diameter / 2).cutThruAll()  # cut the vertical vent holes

        # cut the side slot
        side_slot_cutter_d = 2
        card_width = cadquery.importers.importDXF(str(wrk_dir / "drawings" / "2d.dxf"), include=["pcb"]).faces().val().BoundingBox().ylen
        slot_point = [(0, -height / 2 + pcb_base_offset + pcb_thickness / 2)]
        wp = wp.faces("<X").workplane(**u.cobb).pushPoints(slot_point).slot2D(card_width + side_slot_cutter_d, side_slot_cutter_d).cutBlind(-1 * ((extents[0] - inner[0]) / 2 + inner_fillet))
        # wp = wp.slot2D()
        # wp = wp.faces("<X").workplane(**u.cobb).center(0, -height / 2 + underpocket_airgap - pcb_thickness / 2).circle(side_slot_cutter_d / 2).cutBlind(-1 * (extents[0] - inner[0]) / 2)

        # cut the stopper holes
        # small_pin_top_layer_name = "small_pin_top_clear"  # using slots
        small_pin_top_layer_name = "small_pin_top_clear_individual"
        stopper_holes = cadquery.importers.importDXF(str(wrk_dir / "drawings" / "2d.dxf"), include=[small_pin_top_layer_name]).wires().toPending().extrude(height).translate((0, 0, pin_stopper_drilldown))
        wp = wp.cut(stopper_holes)

        # cut the substrate pockets
        substrate_pockets = cadquery.importers.importDXF(str(wrk_dir / "drawings" / "2d.dxf"), include=["slot_plate_inner_small"]).wires().toPending().extrude(height).translate((0, 0, pocket_depth_drilldown))
        wp = wp.cut(substrate_pockets)

        wp = wp.faces(">Z").edges("not %CIRCLE").chamfer(chamfer)
        wp = wp.faces("<Z").edges("not %CIRCLE").chamfer(chamfer)

        # corner holes (with nuts and nut pockets)
        wp = wp.faces(">Z").workplane(**u.cobb, offset=-nut.nut_thickness).pushPoints(hps).clearanceHole(fastener=nut, fit="Close", counterSunk=False, baseAssembly=wall_hardware)
        wp = wp.faces(">Z").workplane(**u.cobb).sketch().push(hps[0:4:3]).rect(flat_to_flat, nut.nut_diameter, angle=45).reset().push(hps[1:3]).rect(flat_to_flat, nut.nut_diameter, angle=-45).reset().vertices().fillet(nut.nut_diameter / 4).finalize().cutBlind(-nut.nut_thickness)

        # cyl = wp.faces("<Z[-2]").workplane(**u.copo, origin=cq.Vector(0,0,0)).transformed(rotate=cq.Vector(0,-45,0)).cylinder(height=top_cyl_length, radius=gas_hole_diameter/2,  centered=(True,True,True), combine=False)
        # cyl = wp.faces("<Z[-3]").workplane(**u.copo).transformed(rotate=cq.Vector(0,-45,0)).cylinder(height=top_cyl_length, radius=gas_hole_diameter/2,  centered=(True,True,True), combine=False)
        # wp = wp.cut(cyl)

        # chamfers
        # wp = wp.faces(">Z").edges(">>X").chamfer(chamfer)

        # # gas holes with recesses
        # wp = wp.faces("<X").workplane(**u.cobb).center(back_holes_shift, 0).rarray(back_holes_spacing, 1, 2, 1).hole(diameter=gas_fitting_hole_diameter, depth=thickness)
        # # wp = wp.faces("<X").workplane(**u.cobb).center(back_holes_shift, 0).sketch().rarray(back_holes_spacing, 1, 2, 1).rect(gas_fitting_diameter, gas_fitting_flat_to_flat).reset().vertices().fillet(gas_fitting_diameter / 4).finalize().cutBlind(-gas_fitting_recess)
        # wp = wp.faces("<X").workplane(**u.cobb).center(back_holes_shift, 0).sketch().rect(2 * gas_fitting_diameter / 2 + back_holes_spacing, gas_fitting_flat_to_flat).reset().vertices().fillet(gas_fitting_diameter / 4).finalize().cutBlind(-gas_fitting_recess)  # unify the back holes
        # wp = wp.faces(">X").workplane(**u.cobb).rarray(front_holes_spacing, 1, 2, 1).hole(diameter=gas_fitting_hole_diameter, depth=thickness)
        # wp = wp.faces(">X").workplane(**u.cobb).sketch().rarray(front_holes_spacing, 1, 2, 1).rect(gas_fitting_diameter, gas_fitting_flat_to_flat).reset().vertices().fillet(gas_fitting_diameter / 4).finalize().cutBlind(-gas_fitting_recess)

        # cut_side = cadquery.importers.importDXF("drawings/2d.dxf", include=["pcb"]).wires().toPending().extrude(pcb_thickness)
        # wp = wp.cut(cut_side.translate((0, 0, 6.2)))

        # # get pipe fitting geometry
        # a_pipe_fitting = u.import_step(wrk_dir.joinpath("components", "5483T93_Miniature Nickel-Plated Brass Pipe Fitting.step"))
        # a_pipe_fitting = a_pipe_fitting.translate((0, 0, -6.35 - gas_fitting_recess))
        # pipe_fitting_asy = cadquery.Assembly(a_pipe_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=30), name="one_pipe_fitting")

        # # move the pipe fittings to their wall holes
        # wppf = wp.faces(">X").workplane(**u.cobb).center(front_holes_spacing / 2, 0)
        # pipe_fitting_asy.loc = wppf.plane.location
        # wall_hardware.add(pipe_fitting_asy, name="front_right_gas_fitting")
        # wppf = wppf.center(-front_holes_spacing, 0)
        # pipe_fitting_asy.loc = wppf.plane.location
        # wall_hardware.add(pipe_fitting_asy, name="front_left_gas_fitting")
        # wppf = wp.faces("<X").workplane(**u.cobb).center(back_holes_shift + back_holes_spacing / 2, 0)
        # pipe_fitting_asy.loc = wppf.plane.location
        # wall_hardware.add(pipe_fitting_asy, name="rear_left_gas_fitting")
        # wppf = wppf.center(-back_holes_spacing, 0)
        # pipe_fitting_asy.loc = wppf.plane.location
        # wall_hardware.add(pipe_fitting_asy, name="rear_right_gas_fitting")

        # # get bonded washer geometry, part 229-6277
        # bonded_washer = u.import_step(wrk_dir.joinpath("components", "hutchinson_ljf_207242.stp"))
        # bonded_washer = bonded_washer.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 1, 0), angleDegrees=90).translate((0, 0, 1.25))
        # bonded_washer_asy = cadquery.Assembly(bonded_washer, name="one_bonded_washer")

        # # move bonded washers to their wall holes
        # washer_thickness = 2.5
        # wpbw = wp.faces(">X").workplane(**u.cobb, offset=-thickness - washer_thickness).center(-front_holes_spacing / 2, 0)
        # bonded_washer_asy.loc = wpbw.plane.location
        # wall_hardware.add(bonded_washer_asy, name="front_right_bonded_washer")
        # wpbw = wpbw.center(front_holes_spacing, 0)
        # bonded_washer_asy.loc = wpbw.plane.location
        # wall_hardware.add(bonded_washer_asy, name="front_left_bonded_washer")
        # wpbw = wp.faces("<X[-5]").workplane(**u.cobb).center(-back_holes_shift - back_holes_spacing / 2, 0)
        # bonded_washer_asy.loc = wpbw.plane.location
        # wall_hardware.add(bonded_washer_asy, name="rear_right_bonded_washer")
        # wpbw = wpbw.center(back_holes_spacing, 0)
        # bonded_washer_asy.loc = wpbw.plane.location
        # wall_hardware.add(bonded_washer_asy, name="rear_left_bonded_washer")

        # # passthrough details
        # pcb_scr_head_d_safe = 6
        # n_header_pins = 50
        # header_length = n_header_pins / 2 * 2.54 + 7.62  # n*0.1 + 0.3 inches
        # support_block_width = 7
        # pt_pcb_width = 2 * (support_block_width / 2 + pcb_scr_head_d_safe / 2) + header_length
        # pt_pcb_outer_depth = 8.89 + 0.381  # 0.35 + 0.15 inches
        # pt_pcb_inner_depth = 8.89 + 0.381  # 0.35 + 0.15 inches
        # pt_center_offset = 28.65  # so that the internal passthrough connector aligns with the one in the chamber

        # # make the electrical passthrough
        # pt_asy = cadquery.Assembly()  # this will hold the passthrough part that gets created
        # # pcb_asy = cadquery.Assembly()  # this will hold the pcb part that gets created
        # pcb_asy = None  # dont generate the base PCB (will probably later import the detailed board model)
        # hw_asy = cadquery.Assembly()  # this will hold the pcb part that gets created
        # ptt = 5.5  # passthrough thickness, reduce a bit from default (which was half wall thickness) to prevent some thin walls close to an o-ring gland
        # wp = wp.faces("<X").workplane(**u.cobb).center(-pt_center_offset, 0).make_oringer(board_width=pt_pcb_width, board_inner_depth=pt_pcb_inner_depth, board_outer_depth=pt_pcb_outer_depth, wall_depth=thickness, part_thickness=ptt, pt_asy=pt_asy, pcb_asy=pcb_asy, hw_asy=hw_asy)
        # # insert passthrough into assembly
        # for asyo in pt_asy.traverse():
        #     part = asyo[1]
        #     if isinstance(part.obj, cadquery.occ_impl.shapes.Solid):
        #         aso.add(part.obj, name=asyo[0], color=color)
        # if pcb_asy is not None:
        #     # insert pcb into assembly
        #     for asyo in pcb_asy.traverse():  # insert only one solid object
        #         part = asyo[1]
        #         if isinstance(part.obj, cadquery.occ_impl.shapes.Solid):
        #             aso.add(part.obj, name=asyo[0], color=cadquery.Color("DARKGREEN"))
        # # insert hardware into assembly
        # aso.add(hw_asy.toCompound(), name="passthrough hardware")

        # # add in little detailed PCB
        # a_little_pcb = u.import_step(wrk_dir.joinpath("components", "pt_pcb.step")).translate((0, 0, -pcb_thickness / 2))  # shift pcb to be z-centered
        # little_pcb = cadquery.Assembly(a_little_pcb.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 1, 0), angleDegrees=90).rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=90), name="small detailed pcb")
        # asys["squirrel"].add(little_pcb, loc=wp.plane.location, name="little pcb")

        # # for the vac chuck fittings
        # rotation_angle = -155  # degrees
        # vac_fitting_wall_offset = extents[1] / 2 - thickness - inner_fillet - 4  # mounting location offset from center
        # wp = wp.faces(">X").workplane(**u.cobb).center(vac_fitting_wall_offset, 0).tapHole(vac_fitting_screw, depth=thickness + fitting_step_xy[0])
        # vac_chuck_fitting = cadquery.Assembly(a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=rotation_angle), name="outer_wall_vac_fitting")
        # aso.add(vac_chuck_fitting, loc=wp.plane.location, name="vac chuck fitting (wall outer)")

        # nwp = wp.faces(">X").workplane(**u.cobb, invert=True, offset=thickness + fitting_step_xy[0]).center(vac_fitting_wall_offset, 0)
        # vac_chuck_fitting = cadquery.Assembly(a_vac_fitting.rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=-rotation_angle), name="inner_wall_vac_fitting")
        # aso.add(vac_chuck_fitting, loc=nwp.plane.location, name="vac chuck fitting (wall inner)")

        # # that's part number polymax 230X2N70
        o_ring_thickness = 3
        o_ring_inner_diameter = 115
        ooffset = 17  # two times the o-ring path's center offset from the outer edge of the walls
        # cut the lid o-ring groove
        wp = wp.faces(">Z").workplane(**u.cobb).mk_groove(ring_cs=o_ring_thickness, follow_pending_wires=False, ring_id=o_ring_inner_diameter, gland_x=extents[0] - ooffset, gland_y=extents[1] - ooffset, hardware=wall_hardware)

        # # cut the base o-ring groove
        wp = wp.faces("<Z").workplane(**u.cobb).mk_groove(ring_cs=o_ring_thickness, follow_pending_wires=False, ring_id=o_ring_inner_diameter, gland_x=extents[0] - ooffset, gland_y=extents[1] - ooffset, hardware=wall_hardware)

        aso.add(wall_hardware.toCompound(), name="wall_hardware", color=cadquery.Color(hardware_color))
        aso.add(wp, name=name, color=color)  # add the walls bulk

    mkwalls(wrk_dir, asys[as_name], wall_height, center_shift, wall_outer, corner_hole_points, 0, outer_fillet)

    # add in big detailed PCB
    # big_pcb = u.import_step(wrk_dir.joinpath("components", "pcb.step"))
    # asys["squirrel"].add(big_pcb, name="big pcb")

    TwoDToThreeD.outputter(asys, wrk_dir, save_steps=True, save_stls=True)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
