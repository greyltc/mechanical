#!/usr/bin/env python3

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
from typing import cast

setattr(cq.Workplane, "undercutRelief2D", u.undercutRelief2D)


def main():
    # set working directory
    try:
        wrk_dir = Path(__file__).parent
    except Exception as e:
        wrk_dir = Path.cwd()
    print(f"Working directory is {wrk_dir}")
    drawings = {"2d": wrk_dir / "drawings" / "2d.dxf"}

    no_threads = True  # set true to make all the hardware have no threads (much faster, smaller)
    flange_base_height = 0
    flange_bit_thickness = 16.9
    fil_major = 5
    chamf_major = 1
    chamf_minor = 0.5

    def mk_flange_bit(drawings: dict[str, Path], components_dir: Path, flange_base_height: float, thickness: float) -> tuple[cq.Solid | cq.Compound, cq.Assembly]:
        """build the flange bit"""
        hardware = cq.Assembly()  # this being empty causes a warning on output

        flange_corner_screw_spacing = 17.8
        flange_corner_points = [
            (-flange_corner_screw_spacing / 2, -flange_corner_screw_spacing / 2),
            (-flange_corner_screw_spacing / 2, +flange_corner_screw_spacing / 2),
            (+flange_corner_screw_spacing / 2, -flange_corner_screw_spacing / 2),
            (+flange_corner_screw_spacing / 2, +flange_corner_screw_spacing / 2),
        ]

        basex = 26
        basey = 58
        flange_hole_d = 14.8
        base = CQ().box(basex, basey, thickness, centered=(True, True, False)).circle(flange_hole_d / 2).cutThruAll()
        # base = cq.importers.importDXF(str(drawings["2d"]), include=["flange_bit", "flange_hole"]).wires().toPending().extrude(thickness)

        wp = cq.Workplane().add(base.translate((0, 0, -thickness - flange_base_height)))

        flange = u.import_step(components_dir / "SM05F1-Step.step").findSolid().translate((0, 0, 10.0076))
        flange_screw_space = 0.9144
        hardware.add(flange, name="flange")

        adapter_shift = 10.0076 - 3.175  # shift the hardware to the top of the flange
        fiber_adapter = u.import_step(components_dir / "SM05SMA-Step.step").findSolid().rotate((0, 0, 0), (0, 1, 0), 90).translate((7.1746, 10.8567, 29.16169 + adapter_shift))
        hardware.add(cq.Assembly(fiber_adapter), name="adapter")

        ring_shift = 5.18  # put ring under adapter
        ring = u.import_step(components_dir / "SM05RR-Step.step").findSolid().rotate((0, 0, 0), (0, 1, 0), 180).translate((0, 0, 0.82550 + ring_shift))
        hardware.add(cq.Assembly(ring), name="lockring")

        flange_screw_length = thickness
        flange_screw = CheeseHeadScrew(size="M3-0.5", fastener_type="iso14580", length=flange_screw_length, simple=no_threads)  # TODO: insert accu pn

        # flange screws
        wp = wp.faces(">Z").workplane(**u.cobb, offset=flange_screw_space).pushPoints(flange_corner_points).clearanceHole(fastener=flange_screw, fit="Close", baseAssembly=hardware, counterSunk=False)

        # flange nuts with pockets
        flange_nut = HexNut(size="M3-0.5", fastener_type="iso4032")  # TODO: insert accu pn
        flat_to_flat = math.sin(60 * math.pi / 180) * flange_nut.nut_diameter + 0.25
        wp = wp.faces("<Z").workplane(**u.cobb, offset=-flange_nut.nut_thickness - flange_screw_space).pushPoints(flange_corner_points).clearanceHole(fastener=flange_nut, fit="Close", counterSunk=False, baseAssembly=hardware)
        wp = wp.faces("<Z").workplane(**u.cobb).sketch().push(flange_corner_points[0:4:3]).rect(flat_to_flat, flange_nut.nut_diameter, angle=45).reset().push(flange_corner_points[1:3]).rect(flat_to_flat, flange_nut.nut_diameter, angle=-45).reset().vertices().fillet(flange_nut.nut_diameter / 4).finalize().cutBlind(-flange_nut.nut_thickness - flange_screw_space)

        return (wp.findSolid(), hardware)

    def mk_single_holder(drawings, components_dir=wrk_dir / "components") -> dict[str, cq.Assembly | cq.Solid | cq.Compound]:
        hardware = cq.Assembly()  # this being empty causes a warning on output

        v2 = True  # v2=True, v1=False
        subs_xy = 12  # v2=12, v1=30
        subs_tol = 0.2  # substrate and mask pocket is this much bigger than nominal substrate xy dims

        subs_t_max = 2.2  # worst case glass thickness (worst case means thinn)
        subs_t_min = 1.1  # v2=1.1, v1=2.2
        subs = CQ().box(subs_xy, subs_xy, subs_t_max, centered=(True, True, False)).findSolid()
        hardware.add(subs, name="substrate")

        mask_t = 0.4  # worst case mask thickness, v2=0.4, v1=0.2
        mask = CQ().box(subs_xy, subs_xy, mask_t, centered=(True, True, False)).findSolid()
        hardware.add(mask.translate((0, 0, subs_t_max)), name="mask")

        big_pin = False  # 2.54mm spacing pins, v2=false, v1=true
        if big_pin:
            pin_travel = 4.2
            head_length = 2
            pin_nominal_frac = 2 / 3  # fraction of total travel for nominal deflection
            head_diameter = 1.8
            retaining_ring_offset = 5.5  # the offset from max travel of the no-splip-down ring's bottom
            sleeve_length = 18.50  # length before bottom taper
            total_sleeve_length = 23.7
            drill_diameter = 1.75
            pin = u.import_step(components_dir / "S25-022+P25-4023.step").findSolid().rotate((0, 0, 0), (1, 0, 0), 90)
            pin_nom_offset = head_length + (1 - pin_nominal_frac) * pin_travel
            pin = pin.translate((0, 0, -pin_nom_offset))
            void_head_offset = 0.2  # make the pin void diameter this much larger than that of the pin head
            upper_pin_void = cq.Solid.makeCylinder((head_diameter + void_head_offset) / 2, head_length + pin_travel + retaining_ring_offset).move(cq.Location((0, 0, -pin_nom_offset - retaining_ring_offset)))
            lower_pin_void = cq.Solid.makeCylinder(drill_diameter / 2, head_length + pin_travel + total_sleeve_length).move(cq.Location((0, 0, -total_sleeve_length)))
            pin_void = CQ(upper_pin_void).union(lower_pin_void).findSolid()

            void_depth = subs_t_max + mask_t + pin_nominal_frac * pin_travel
        else:  # 1.27mm spacing pins
            pin_travel = 2.65
            head_length = 0.9
            pin_nominal_frac = 2 / 3  # fraction of total travel for nominal deflection
            head_diameter = 0.9
            retaining_ring_offset = 2.50  # the offset from max travel of the no-splip-down ring's bottom
            sleeve_length = 12.75  # length before bottom taper
            total_sleeve_length = 17.75
            drill_diameter = 0.95
            pin = u.import_step(components_dir / "P13-4023+S13-503.step").findSolid().rotate((0, 0, 0), (1, 0, 0), 90)
            pin_nom_offset = head_length + (1 - pin_nominal_frac) * pin_travel
            pin = pin.translate((0, 0, -pin_nom_offset))
            void_head_offset = 0.2  # make the pin void diameter this much larger than that of the pin head
            upper_pin_void = cq.Solid.makeCylinder((head_diameter + void_head_offset) / 2, head_length + pin_travel + retaining_ring_offset + 10).move(cq.Location((0, 0, -pin_nom_offset - retaining_ring_offset)))
            lower_pin_void = cq.Solid.makeCylinder(drill_diameter / 2, head_length + pin_travel + total_sleeve_length).move(cq.Location((0, 0, -total_sleeve_length)))
            pin_void = CQ(upper_pin_void).union(lower_pin_void).findSolid()

            void_depth = subs_t_max + mask_t + pin_nominal_frac * pin_travel

        pusher_screw_len = 10  # v2=10, v1=15
        pusher_screw = CounterSunkScrew(size="M6-1", fastener_type="iso14581", length=pusher_screw_len, simple=no_threads)  # TODO: add pn

        holder_base_height = sleeve_length + pin_nom_offset

        pusher_t = 4.1  # the extra 0.1 here is to give a sharp edge for mask registration
        pusher_shrink = 0.4  # shrink the x+y so that zero spaced holders don't have interfering pushers
        pusher_aperture_chamfer = 4
        pusher_aperture_fillet = 2  # v2=2, v1=5
        pusher_screw_offset = 18  # v2=17, v1=14
        pusher_mount_spacing = subs_xy + pusher_screw_offset
        pusher_w = pusher_mount_spacing + 14
        y_blocks_total = 2  # pusher_downer blocks, with of both together v2=2, v1=6
        x_blocks_total = 2  # pusher_downer blocks, with of both together v2=2, v1=0
        light_aperture_x = subs_xy + subs_tol - x_blocks_total
        light_aperture_y = subs_xy + subs_tol - y_blocks_total
        pusher_height = void_depth - subs_t_min  # the length of the push downer bits, this should be void_depth to accept 0 thickness substrates, but can be less to allow wider acceptance angle
        walls_thickness = pusher_aperture_chamfer + 2 - x_blocks_total
        walls_x = subs_xy + subs_tol + 2 * walls_thickness
        pusher = CQ().workplane(offset=pusher_height + subs_t_max + mask_t).box(walls_x - pusher_shrink, pusher_w - pusher_shrink, pusher_t, centered=(True, True, False))
        pusher = pusher.faces("<Z").workplane().rect(subs_xy, subs_xy).extrude(pusher_height)
        pusher = pusher.sketch().rect(light_aperture_x, light_aperture_y).vertices().fillet(pusher_aperture_fillet).finalize().cutThruAll()
        pusher = cast(CQ, pusher)  # workaround for sketch.finalize() not returning the correct type
        if not v2:
            pusher = pusher.faces("<Z").workplane().rect(light_aperture_x, light_aperture_y).cutBlind(-pusher_height)  # make the pusher blocks square
        pusher = pusher.edges("|Z and (<X or >X)").fillet(fil_major)
        pusher = pusher.faces(">Z[1]").edges("<X").chamfer(chamf_major)
        pusher = pusher.faces(">Z").edges("<<X[2]").chamfer(pusher_aperture_chamfer)
        pusher = pusher.faces(">Z").edges("<X").chamfer(chamf_minor)
        # pusher = pusher.faces("<Z").chamfer(chamf_minor)  # don't chamfer the ends of the pusher, they might need to register masks
        pusher = pusher.faces(">Z").workplane().rarray(1, pusher_mount_spacing, 1, 2).clearanceHole(pusher_screw, fit="Close", baseAssembly=hardware)

        walls_y = pusher_w
        corner_round_radius = 4  # v2=4, v1=10
        holder = CQ().box(walls_x, walls_y, holder_base_height, centered=(True, True, False)).translate((0, 0, -holder_base_height))
        void_part = CQ().box(walls_x, walls_y, void_depth, centered=(True, True, False)).undercutRelief2D(subs_xy + subs_tol, subs_xy + subs_tol, corner_round_radius).cutThruAll()
        holder = holder.union(void_part)

        # pin array parameters
        pmajor_x = 3  # v2=3, v1=5.08
        pminor_x = 1.27  # v2=1.27, v1=2.5
        nx = 3  # v2=3, v1=5
        py = 11.27  # v2=11.27, v1=24

        dev_pocket_d = head_length + 0.2  # pocket below devices
        if v2:
            holder = holder.faces(">Z").workplane().undercutRelief2D(py, py, corner_round_radius)
        else:
            holder = holder.faces(">Z").workplane().undercutRelief2D(light_aperture_x, py, corner_round_radius)

        holder = cast(CQ, holder)  # workaround for undercutRelief2D() not returning the correct type
        holder = holder.cutBlind(-void_depth - dev_pocket_d)

        def pvf(loc: cq.Location):
            """returns a pin void shape for the cutEach function (ignore z movement)"""
            pos = loc.position()
            return pin_void.translate((pos.x, pos.y, 0))

        def addpin(vec: cq.Vector):
            """adds a located pin to the hardware, (ignore z movement)"""
            hardware.add(pin.translate((vec.x, vec.y, 0)))

        # cut the pin array holes
        pin_spotsA = CQ().center(-pminor_x / 2, 0).rarray(pmajor_x, py, nx, 2).vals()
        pin_spotsB = CQ().center(+pminor_x / 2, 0).rarray(pmajor_x, py, nx, 2).vals()
        pin_spots = pin_spotsA + pin_spotsB
        if v2:
            pin_spotsC = CQ().rarray(py, pminor_x, 2, 2).vals()
            pin_spots += pin_spotsC

        holder = holder.workplane(origin=(0, 0)).add(pin_spots).cutEach(pvf)

        if not no_threads:
            for pin_spot in pin_spots:
                addpin(pin_spot)

        # bottom PCB through hole clearance void
        pcb_bot_void_d = 5
        pcbvx = 10  # v2=10, v1=25
        pcbvy = 10  # v2=10, v1=20
        pcbvr = 2.5  # v2=2.5, v1=5
        holder = holder.faces("<Z").workplane(origin=(0, 0)).sketch().rect(pcbvx, pcbvy).vertices().fillet(pcbvr).finalize()
        holder = cast(CQ, holder)  # workaround for sketch.finalize() not returning the correct type
        holder = holder.cutBlind(-pcb_bot_void_d)

        pcbx = 13  # v2=13, v1=30
        pcby = 13  # v2=13, v1=30
        pcbt = 1.6
        pcbpinr = 0.4  # v2=0.4, v1=0.8
        pcbr = 2  # corner fillet radius, v2=2, v1=5
        pcb = holder.faces("<Z").workplane(origin=(0, 0)).sketch().rect(pcbx, pcby).vertices().fillet(pcbr).finalize()
        pcb = cast(CQ, pcb)  # workaround for sketch.finalize() not returning the correct type
        pcb = pcb.extrude(pcbt, combine=False).findSolid()
        pcb = CQ(pcb).faces("<Z").workplane(origin=(0, 0)).add(pin_spots).circle(pcbpinr).extrude(pcbt + holder_base_height, combine="cut")
        if v2:
            # pcb header pin holes
            hph_dia = 0.89  # header pin hole diameter
            hps = 2
            hpnx = 5
            hpny = 4
            # pcb = pcb.faces("<Z").workplane(origin=(0, 0)).rarray(hps, hps, hpnx, hpny).circle(hph_dia / 2).extrude(pcbt + holder_base_height, combine="cut")
            pcb = pcb.faces("<Z").workplane(origin=(0, 0)).rarray(hps, hps, hpnx, hpny).circle(hph_dia / 2).extrude(-pcbt, combine="cut")

        if not no_threads:
            if v2:
                # add in the pin header
                header = header_stack = u.import_step(components_dir / "TMMH-105-01-T-Q.stp").findSolid().rotate((0, 0, 0), (1, 0, 0), -90)
                hardware.add(header.located(cq.Location((0, 0, -holder_base_height - pcbt))))
            else:
                # add in the header and IDC connector stack
                header_stack = u.import_step(components_dir / "SHF213+SHB11.step").findSolid().rotate((0, 0, 0), (1, 0, 0), -180)

                hardware.add(header_stack.located(cq.Location((0, +2 * 2.54, -holder_base_height - pcbt))))
                hardware.add(header_stack.located(cq.Location((0, -2 * 2.54, -holder_base_height - pcbt))))

        # pusher screw interface stuff here
        bot_screw_len = 10  # v2=10, v1=15
        bot_screw = CounterSunkScrew(size="M6-1", fastener_type="iso14581", length=bot_screw_len, simple=no_threads)  # TODO: add pn

        c_flat_to_flat = 10
        c_flat_to_flat = c_flat_to_flat + 0.4  # add fudge factor so it can slide in
        c_diameter = c_flat_to_flat / (math.cos(math.tanh(1 / math.sqrt(3))))
        if v2:
            coupler_len = 15
            coupler = u.import_step(components_dir / "Download_STEP_970150611 (rev1).stp").findSolid().translate((0, 0, -coupler_len / 2))
        else:
            coupler_len = 20
            coupler = u.import_step(components_dir / "Download_STEP_970200611 (rev1).stp").findSolid().translate((0, 0, -coupler_len / 2))

        holder = holder.faces(">Z").workplane(origin=(0, 0)).sketch().rarray(1, pusher_mount_spacing, 1, 2).rect(c_diameter, c_flat_to_flat).reset().vertices().fillet(c_diameter / 4).finalize().cutBlind(-coupler_len)
        holder = cast(CQ, holder)  # workaround for sketch.finalize() not returning the correct type
        mount_points = holder.faces(">Z").workplane(origin=(0, 0)).rarray(1, pusher_mount_spacing, 1, 2).vals()
        for mount_point in mount_points:
            hardware.add(coupler.located(cq.Location(mount_point.toTuple())))

        holder = holder.faces("<Z").workplane(origin=(0, 0)).rarray(1, pusher_mount_spacing, 1, 2).clearanceHole(bot_screw, fit="Close", baseAssembly=hardware)

        out = {"holder": holder.findSolid()}
        out["pusher"] = pusher.findSolid()
        out["pcb"] = pcb
        out["hardware"] = hardware

        return out

    # make the pieces
    flange_bit, flange_hardware = mk_flange_bit(drawings=drawings, components_dir=wrk_dir / "components", flange_base_height=flange_base_height, thickness=flange_bit_thickness)
    holder_parts = mk_single_holder(drawings=drawings, components_dir=wrk_dir / "components")
    holder = holder_parts["holder"]
    # pin_holder = holder_parts["pin_holder"]
    pusher = holder_parts["pusher"]
    pcb = holder_parts["pcb"]
    holder_hw = holder_parts["hardware"]

    wp_single = CQ(holder)

    # mod the 1x1 holder with bottom shrouds
    shroud_width = 3.5  # sum of both together, v2=3.5, v1=4
    shroud_height = 25
    holder1x1 = CQ(holder).faces("<Z").wires().toPending().extrude(-shroud_height)
    holder1x1 = holder1x1.edges("|Z and >X").fillet(fil_major)  # must do this now because it will crash later
    bb1x1 = holder1x1.findSolid().BoundingBox()
    xlen1 = bb1x1.xlen
    ylen1 = bb1x1.ylen
    holder1x1 = holder1x1.faces("<Z").workplane(origin=(0, 0)).rect(xlen1 - 2 * shroud_width, ylen1).cutBlind(-shroud_height).findSolid()

    wp_2x2 = CQ(holder.translate((xlen1 / 2, ylen1 / 2, 0)))
    wp_2x2 = wp_2x2.union(holder.translate((+xlen1 / 2, -ylen1 / 2, 0)))
    wp_2x2 = wp_2x2.union(holder.translate((-xlen1 / 2, +ylen1 / 2, 0)))
    wp_2x2 = wp_2x2.union(holder.translate((-xlen1 / 2, -ylen1 / 2, 0)))

    # assemble the pieces
    hardware2x2 = cq.Assembly(name="all_hardware")  # this being empty causes a warning on output
    hardware2x1 = cq.Assembly(name="all_hardware")  # this being empty causes a warning on output
    hardware1x1 = cq.Assembly(name="all_hardware")  # this being empty causes a warning on output
    hardware_single = cq.Assembly(name="all_hardware")  # this being empty causes a warning on output

    flange_z_shift = -5
    hardware2x1.add(flange_hardware, loc=cq.Location((0, 0, flange_z_shift)), name="flange_hardware")
    hardware1x1.add(flange_hardware, loc=cq.Location((0, 0, flange_z_shift)), name="flange_hardware")
    flange_bit = flange_bit.translate((0, 0, flange_z_shift))
    # hardware.add(flange_hardware._copy().translate((0, 0, flange_z_shift)))
    holder_shift = flange_bit.BoundingBox().xmax + holder.BoundingBox().xmax
    wp_2x1 = CQ(flange_bit)
    wp_1x1 = CQ(flange_bit)
    wp_2x1 = wp_2x1.union(holder.translate((+holder_shift, 0, 0)))
    wp_1x1 = wp_1x1.union(holder1x1.translate((+holder_shift, 0, 0)))
    wp_2x1 = wp_2x1.union(holder.translate((-holder_shift, 0, 0)))
    hardware2x2.add(holder_hw, loc=cq.Location((-xlen1 / 2, -ylen1 / 2, 0)), name="holder_11_hardware")
    hardware2x2.add(holder_hw, loc=cq.Location((+xlen1 / 2, -ylen1 / 2, 0)), name="holder_21_hardware")
    hardware2x2.add(holder_hw, loc=cq.Location((-xlen1 / 2, +ylen1 / 2, 0)), name="holder_12_hardware")
    hardware2x2.add(holder_hw, loc=cq.Location((+xlen1 / 2, +ylen1 / 2, 0)), name="holder_22_hardware")
    hardware2x1.add(holder_hw, loc=cq.Location((+holder_shift, 0, 0)), name="holder_a_hardware")
    hardware1x1.add(holder_hw, loc=cq.Location((+holder_shift, 0, 0)), name="holder_a_hardware")
    hardware2x1.add(holder_hw, loc=cq.Location((-holder_shift, 0, 0)), name="holder_b_hardware")
    hardware_single.add(holder_hw, name="single_hardware")

    # add the mounting screw for the 1x1
    side_screw_len = 45
    side_screw_max_head_d = 9
    side_screw_start_depth = 26
    side_screw = CheeseHeadScrew(size="M4-0.7", fastener_type="iso14580", length=side_screw_len, simple=no_threads)  # TODO: add pn
    wp_1x1 = wp_1x1.faces("<X").workplane(offset=-side_screw_start_depth, **u.cobb).clearanceHole(side_screw, fit="Close", baseAssembly=hardware1x1, counterSunk=False)
    wp_1x1 = cast(CQ, wp_1x1)  # workaround for sketch.clearanceHole() not returning the correct type
    wp_1x1 = wp_1x1.faces("<X").workplane(**u.cobb).circle(side_screw_max_head_d / 2).cutBlind(-side_screw_start_depth)

    bb1x1 = wp_1x1.findSolid().BoundingBox()

    # side nut with pockets
    side_nut = HexNut(size="M4-0.7", fastener_type="iso4032")  # TODO: insert accu pn
    flat_to_flat = math.sin(60 * math.pi / 180) * side_nut.nut_diameter + 0.25
    wp_1x1 = wp_1x1.faces(">X").workplane(origin=(0, 0), offset=-side_nut.nut_thickness).center(0, bb1x1.zmin + flange_bit_thickness / 2 + shroud_height).clearanceHole(fastener=side_nut, fit="Close", counterSunk=False, baseAssembly=hardware1x1)
    wp_1x1 = cast(CQ, wp_1x1)  # workaround for sketch.clearanceHole() not returning the correct type
    wp_1x1 = wp_1x1.faces(">X").workplane(origin=(0, 0)).center(0, bb1x1.zmin + flange_bit_thickness / 2 + shroud_height).sketch().rect(flat_to_flat, side_nut.nut_diameter, angle=90).reset().vertices().fillet(side_nut.nut_diameter / 4).finalize().cutBlind(-side_nut.nut_thickness)
    wp_1x1 = cast(CQ, wp_1x1)  # workaround for sketch.clearanceHole() not returning the correct type

    # add the bottom standoff shrouds for the 2x1
    wp_2x1 = wp_2x1.faces("<Z").wires().toPending().extrude(-shroud_height)
    bb2x1 = wp_2x1.findSolid().BoundingBox()
    xlen = bb2x1.xlen
    ylen = bb2x1.ylen
    wp_2x1 = wp_2x1.faces("<Z").workplane(origin=(0, 0)).rect(xlen - 2 * shroud_width, ylen).cutBlind(-shroud_height)

    # add the bottom standoff shrouds for the 2x2
    wp_2x2 = wp_2x2.faces("<Z").wires().toPending().extrude(-shroud_height)
    bb2x2 = wp_2x2.findSolid().BoundingBox()
    xlen = bb2x2.xlen
    ylen = bb2x2.ylen
    wp_2x2 = wp_2x2.faces("<Z").workplane(origin=(0, 0)).rect(xlen - 2 * shroud_width, ylen).cutBlind(-shroud_height)

    # make fillets and chamfers on the 2x2 big piece
    wp_2x2 = wp_2x2.edges("|Z and (<X or >X)").fillet(fil_major)
    wp_2x2 = wp_2x2.faces(">Z").edges("<X").chamfer(chamf_major)
    # wp_2x2 = wp_2x2.faces(">Z").edges(">X").chamfer(chamf_major)

    # make fillets and chamfers on the 2x1 big piece
    wp_2x1 = wp_2x1.edges("|Z and (<X or >X)").fillet(fil_major)
    wp_2x1 = wp_2x1.faces(">Z").edges("<X").chamfer(chamf_major)
    wp_2x1 = wp_2x1.faces(">Z").edges(">X").chamfer(chamf_major)

    # make fillets and chamfers on the 1x1 big piece
    wp_1x1 = wp_1x1.edges("|Z and <X").fillet(fil_major)  # can only do one of these now because the 2nd will crash (done above instead)
    # wp_1x1 = wp_1x1.edges("|Z and (<X or >X)").fillet(fil_major)
    wp_1x1 = wp_1x1.faces(">Z").edges("<X").chamfer(chamf_major)
    wp_1x1 = wp_1x1.faces(">Z").edges(">X").chamfer(chamf_major)

    # make the fillets for the only holder
    wp_single = wp_single.edges("|Z and (<X or >X)").fillet(fil_major)
    wp_single = wp_single.faces(">Z").edges("<X").chamfer(chamf_major)

    # pusher = CQ(pusher).edges("|Z and (<X or >X)").fillet(fil_major).findSolid()

    pusher_2x2 = cq.Assembly()
    pusher_2x1 = cq.Assembly()
    pusher_1x1 = cq.Assembly()
    pusher_single = cq.Assembly()
    pusher_single.add(pusher, name="pusher_single")
    pusher_2x2.add(pusher, loc=cq.Location((-xlen1 / 2, -ylen1 / 2, 0)), name="holder_11_pusher")
    pusher_2x2.add(pusher, loc=cq.Location((+xlen1 / 2, -ylen1 / 2, 0)), name="holder_21_pusher")
    pusher_2x2.add(pusher, loc=cq.Location((-xlen1 / 2, +ylen1 / 2, 0)), name="holder_12_pusher")
    pusher_2x2.add(pusher, loc=cq.Location((+xlen1 / 2, +ylen1 / 2, 0)), name="holder_22_pusher")
    pusher_1x1.add(pusher, loc=cq.Location((+holder_shift, 0, 0)), name="holder_a_pusher")
    pusher_2x1.add(pusher, loc=cq.Location((+holder_shift, 0, 0)), name="holder_a_pusher")
    pusher_2x1.add(pusher, loc=cq.Location((-holder_shift, 0, 0)), name="holder_b_pusher")

    pcb2x2 = cq.Assembly()
    pcb2x1 = cq.Assembly()
    pcb1x1 = cq.Assembly()
    pcb_single = cq.Assembly()
    pcb_single.add(pcb, name="holder_pcb")
    pcb2x2.add(pcb, loc=cq.Location((-xlen1 / 2, -ylen1 / 2, 0)), name="holder_11_pcb")
    pcb2x2.add(pcb, loc=cq.Location((+xlen1 / 2, -ylen1 / 2, 0)), name="holder_21_pcb")
    pcb2x2.add(pcb, loc=cq.Location((-xlen1 / 2, +ylen1 / 2, 0)), name="holder_12_pcb")
    pcb2x2.add(pcb, loc=cq.Location((+xlen1 / 2, +ylen1 / 2, 0)), name="holder_22_pcb")
    pcb1x1.add(pcb, loc=cq.Location((+holder_shift, 0, 0)), name="holder_a_pcb")
    pcb2x1.add(pcb, loc=cq.Location((+holder_shift, 0, 0)), name="holder_a_pcb")
    pcb2x1.add(pcb, loc=cq.Location((-holder_shift, 0, 0)), name="holder_b_pcb")

    twox2 = cq.Assembly(wp_2x2.findSolid(), name="holder")
    hoye_2x1 = cq.Assembly(wp_2x1.findSolid(), name="holder")
    hoye_1x1 = cq.Assembly(wp_1x1.findSolid(), name="holder")
    onex1 = cq.Assembly(wp_single.findSolid(), name="holder")
    onex1.add(pusher_single, name="pusher")
    twox2.add(pusher_2x2, name="pushers")
    hoye_2x1.add(pusher_2x1, name="pushers")
    hoye_1x1.add(pusher_1x1, name="pusher")
    hoye_2x1.add(pcb2x1, name="pcbs")
    hoye_1x1.add(pcb1x1, name="pcbs")
    onex1.add(pcb_single, name="pcb")
    twox2.add(pcb2x2, name="pcbs")
    hoye_2x1.add(hardware2x1, name="hardware")
    hoye_1x1.add(hardware1x1, name="hardware")
    onex1.add(hardware_single, name="hardware")
    twox2.add(hardware2x2, name="hardware")

    asys = {"hoye_2x1": {"assembly": hoye_2x1}}
    asys["hoye_1x1"] = {"assembly": hoye_1x1}
    asys["1x1"] = {"assembly": onex1}
    asys["2x2"] = {"assembly": twox2}

    if "show_object" in globals():  # we're in cq-editor

        def lshow_object(*args, **kwargs):
            return show_object(*args, **kwargs)

    else:
        lshow_object = None

    TwoDToThreeD.outputter(asys, wrk_dir, save_steps=True, save_stls=False, show_object=lshow_object)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
