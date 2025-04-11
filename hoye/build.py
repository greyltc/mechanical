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

    no_threads = False  # set true to make all the hardware have no threads (much faster, smaller)
    version = "hoye12"  # "joe" for 12x12, "yen", "hoye", "snaith" or hoye12
    flange_base_height = 0
    flange_bit_thickness = 16.9
    fil_major = 5
    chamf_major = 1
    chamf_minor = 0.5

    def mk_flange_bit(drawings: dict[str, Path], components_dir: Path, flange_base_height: float, thickness: float, whole_width: float) -> tuple[cq.Solid | cq.Compound, cq.Assembly]:
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
        basey = whole_width
        flange_hole_d = 14.8
        base = CQ().box(basex, basey, thickness, centered=(True, True, False)).circle(flange_hole_d / 2).cutThruAll()

        wp = cq.Workplane().add(base.translate((0, 0, -thickness - flange_base_height)))

        flange = u.import_step(components_dir / "SM05F1-Step.step")
        if flange:
            flange = flange.findSolid().translate((0, 0, 10.0076))
            flange_screw_space = 0.9144
            hardware.add(flange, name="flange")

        adapter_shift = 10.0076 - 3.175  # shift the hardware to the top of the flange
        fiber_adapter = u.import_step(components_dir / "SM05SMA-Step.step")
        if fiber_adapter:
            fiber_adapter = fiber_adapter.findSolid().rotate((0, 0, 0), (0, 1, 0), 90).translate((7.1746, 10.8567, 29.16169 + adapter_shift))
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

        if (version == "joe") or (version == "hoye12"):
            subs_xy = 12
        else:
            subs_xy = 30
        subs_tol = 0.2  # substrate and mask pocket is this much bigger than nominal substrate xy dims

        # maximum substrate thickness to handle
        if version == "yen":
            subs_t_max = 2.5
        else:
            subs_t_max = 2.2

        # minimum substrate thickness to handle
        if (version == "joe") or (version == "hoye12"):
            subs_t_min = 1.1
        elif version == "hoye":
            subs_t_min = 2.2
        else:
            subs_t_min = 0

        # substrate thickness for model
        if version == "hoye":
            subs_t = 2.2
        else:
            subs_t = 1.1

        subs = CQ().box(subs_xy, subs_xy, subs_t, centered=(True, True, False)).findSolid()
        hardware.add(subs, name="substrate")

        if (version == "joe") or (version == "hoye12"):
            mask_t = 0.4  # worst case mask thickness, v2=0.4, v1=0.2
        else:
            mask_t = 0.2  # worst case mask thickness, v2=0.4, v1=0.2
        mask = CQ().box(subs_xy, subs_xy, mask_t, centered=(True, True, False)).findSolid()
        hardware.add(mask.translate((0, 0, subs_t)), name="mask")

        if (version == "joe") or (version == "hoye12"):
            big_pin = False  # 2.54mm spacing pins, v2=false, v1=true
        else:
            big_pin = True  # 2.54mm spacing pins, v2=false, v1=true

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
            lower_pin_void = cq.Solid.makeCylinder(drill_diameter / 2, head_length + pin_travel + total_sleeve_length + pin_nom_offset).move(cq.Location((0, 0, -total_sleeve_length - pin_nom_offset)))
            pin_void = CQ(upper_pin_void).union(lower_pin_void).findSolid()

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
            lower_pin_void = cq.Solid.makeCylinder(drill_diameter / 2, head_length + pin_travel + total_sleeve_length + pin_nom_offset).move(cq.Location((0, 0, -total_sleeve_length - pin_nom_offset)))
            pin_void = CQ(upper_pin_void).union(lower_pin_void).findSolid()

        void_depth = subs_t_max + mask_t + pin_nominal_frac * pin_travel

        if (version == "joe") or (version == "hoye12"):
            pusher_screw_len = 10  # v2=10, v1=15
            holder_base_height = total_sleeve_length + pin_nom_offset - 1.6/2
        else:
            pusher_screw_len = 15  # v2=10, v1=15
            holder_base_height = sleeve_length + pin_nom_offset
        pusher_screw = CounterSunkScrew(size="M6-1", fastener_type="iso14581", length=pusher_screw_len, simple=no_threads)  # TODO: add pn


        pusher_aperture_chamfer = 4
        pusher_t = pusher_aperture_chamfer + 0.1  # the extra 0.1 here is to give a sharp edge for mask registration
        pusher_shrink = 0.4  # shrink the x+y so that zero spaced holders don't have interfering pushers

        if (version == "joe") or (version == "hoye12"):
            pusher_aperture_fillet = 2  # v2=2, v1=5
            pusher_mount_offset = 7.9  # center from top edge of fillet
            y_blocks_total = 2  # pusher_downer blocks, with of both together v2=2, v1=6
            if version == "joe":
                x_blocks_total = 2  # pusher_downer blocks, with of both together v2=2, v1=0
            elif version == "hoye12":
                x_blocks_total = 0
        else:
            pusher_aperture_fillet = 5  # v2=2, v1=5
            pusher_mount_offset = 5.9  # center from top edge of fillet
            y_blocks_total = 6  # pusher_downer blocks, with of both together v2=2, v1=6
            x_blocks_total = 0  # pusher_downer blocks, with of both together v2=2, v1=0
        light_aperture_x = subs_xy + subs_tol - x_blocks_total
        light_aperture_y = subs_xy + subs_tol - y_blocks_total
        if version == "yen":
            pusher_mount_spacing = light_aperture_x + 2 * pusher_mount_offset + 2 * pusher_aperture_chamfer
        else:
            pusher_mount_spacing = light_aperture_y + 2 * pusher_mount_offset + 2 * pusher_aperture_chamfer
        short_wall_thickness = 1 - 0.15  # wall thickness in the shorter direction, fudge by 0.15 to get on a 40mm pitch
        long_wall_fudge = 0.2  # fidge long wall to fit comfortably on a 58mm pitch
        if version == "yen":
            walls_x = pusher_mount_spacing + 14 - long_wall_fudge
            walls_y = subs_xy + subs_tol + 2 * pusher_aperture_chamfer + 2 * short_wall_thickness - x_blocks_total
        else:
            walls_y = pusher_mount_spacing + 14 - long_wall_fudge
            walls_x = subs_xy + subs_tol + 2 * pusher_aperture_chamfer + 2 * short_wall_thickness - x_blocks_total
        pusher_x = walls_x - pusher_shrink
        pusher_y = walls_y - pusher_shrink
        pusher_height = void_depth - subs_t_min  # the length of the push downer bits, this should be void_depth to accept 0 thickness substrates, but can be less to allow wider acceptance angle
        pusher = CQ().workplane(offset=pusher_height + subs_t + mask_t).box(pusher_x, pusher_y, pusher_t, centered=(True, True, False))
        pusher = pusher.faces("<Z").workplane().rect(subs_xy, subs_xy).extrude(pusher_height)
        pusher = pusher.sketch().rect(light_aperture_x, light_aperture_y).vertices().fillet(pusher_aperture_fillet).finalize().cutThruAll()
        pusher = cast(CQ, pusher)  # workaround for sketch.finalize() not returning the correct type
        if not (version == "joe") or (version == "hoye12"):
            pusher = pusher.faces("<Z").workplane().rect(light_aperture_x, light_aperture_y).cutBlind(-pusher_height)  # make the pusher blocks square
        pusher = pusher.edges("|Z and (<X or >X)").fillet(fil_major)
        pusher = pusher.faces(">Z").edges("<<X[2]").chamfer(pusher_aperture_chamfer)
        if (version == "joe") or (version == "hoye12"):
            # extract the pusher windows
            cut_size = [18.2, 18.2, 10]
            pusher_win = pusher.intersect(CQ().box(cut_size[0], cut_size[1], cut_size[2], centered=(True, True, False))).translate((0,0,-pusher_height - subs_t - mask_t-pusher_t))
            #pusher_win = hpc.cut(holder).translate((0,pusher_mount_spacing/2,-void_depth)).findSolid().Solids()[0]
            pusher_win = pusher_win.findSolid()
        else:
            pusher_win = CQ()
        pusher = pusher.faces(">Z[1]").edges("<X").chamfer(chamf_major)
        pusher = pusher.faces(">Z").edges("<X").chamfer(chamf_minor)
        # pusher = pusher.faces("<Z").chamfer(chamf_minor)  # don't chamfer the ends of the pusher, they might need to register masks
        if version == "yen":
            pusher = pusher.faces(">Z").workplane().rarray(pusher_mount_spacing, 1, 2, 1).clearanceHole(pusher_screw, fit="Close", baseAssembly=hardware)
        else:
            pusher = pusher.faces(">Z").workplane().rarray(1, pusher_mount_spacing, 1, 2).clearanceHole(pusher_screw, fit="Close", baseAssembly=hardware)

        if (version == "joe") or (version == "hoye12"):
            corner_round_radius = 4  # v2=4, v1=10
        else:
            corner_round_radius = 10  # v2=4, v1=10
        holder_box = CQ().box(walls_x, walls_y, holder_base_height, centered=(True, True, False)).translate((0, 0, -holder_base_height))
        holder = holder_box
        void_box = CQ().box(walls_x, walls_y, void_depth, centered=(True, True, False))
        void_part = void_box.undercutRelief2D(subs_xy + subs_tol, subs_xy + subs_tol, corner_round_radius).cutThruAll()
        holder = holder.union(void_part)
        holder_box = holder_box.union(void_box)

        # pin array parameters
        if (version == "joe") or (version == "hoye12"):
            pmajor_x = 3
            pminor_x = 1.27
            nx = 3  # v2=3, v1=5
            py = 11.27  # v2=11.27, v1=24
        else:
            pmajor_x = 5.08
            if version == "hoye":
                pminor_x = 2.5
            else:
                pminor_x = 2.54
            nx = 5  # v2=3, v1=5
            py = 24  # v2=11.27, v1=24

        # pocket below devices
        # dev_pocket_d = head_length + 0.2
        dev_pocket_d = pin_nom_offset

        if (version == "joe") or (version == "hoye12"):
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
        if (version == "joe") or (version == "hoye12"):
            pin_spotsC = CQ().rarray(py, pminor_x, 2, 2).vals()
            pin_spots += pin_spotsC

        if version == "hoye12":
            pin_psots = []
            y = 5.6350
            x = 5.3850
            pin_psots.append((x, y, 0))
            pin_psots.append((x-1.27, y, 0))
            pin_psots.append((x, -y, 0))
            pin_psots.append((x-1.27, -y, 0))
            x = 0.6350
            pin_psots.append((x, y, 0))
            pin_psots.append((x-1.27, y, 0))
            pin_psots.append((x, -y, 0))
            pin_psots.append((x-1.27, -y, 0))
            x = -1.8650
            pin_psots.append((x, y, 0))
            pin_psots.append((x-1.27, y, 0))
            pin_psots.append((x, -y, 0))
            pin_psots.append((x-1.27, -y, 0))
            x = -4.3650
            pin_psots.append((x, y, 0))
            pin_psots.append((x-1.27, y, 0))
            pin_psots.append((x, -y, 0))
            pin_psots.append((x-1.27, -y, 0))
            pin_spots = [cq.Vector(p) for p in pin_psots]

        holder = holder.workplane(origin=(0, 0)).add(pin_spots).cutEach(pvf)

        if (version == "joe") or (version == "hoye12"):
            # make a print of the central void
            cv_print = holder_box.cut(holder).translate((0,0,-void_depth)).findSolid()
        else:
            cv_print = CQ()

        if not no_threads:
            for pin_spot in pin_spots:
                addpin(pin_spot)

        # bottom PCB through hole clearance void
        pcb_bot_void_d = 5
        if (version == "joe") or (version == "hoye12"):
            if version == "joe":
                pcbvx = 10  # v2=10, v1=25
                pcbvy = 10  # v2=10, v1=20
            elif version == "hoye12":
                pcbvx = 21
                pcbvy = 8  # v2=10, v1=20
            pcbvr = 2  # v2=2, v1=5
        else:
            pcbvx = 25  # v2=10, v1=25
            pcbvy = 20  # v2=10, v1=20
            pcbvr = 5  # v2=2, v1=5

        if version != "joe":
            holder = holder.faces("<Z").workplane(origin=(0, 0)).sketch().rect(pcbvx, pcbvy).vertices().fillet(pcbvr).finalize()
            holder = cast(CQ, holder)  # workaround for sketch.finalize() not returning the correct type
            holder = holder.cutBlind(-pcb_bot_void_d)

        if (version == "joe") or (version == "hoye12"):
            if version == "joe":
                pcbx = 13  # v2=13, v1=30
                pcby = 13  # v2=13, v1=30
            elif version == "hoye12":
                pcbx = 21.5
                pcby = 15
            pcbt = 1.6
            pcbpinr = 0.4  # v2=0.4, v1=0.8
            pcbr = 2  # corner fillet radius, v2=2, v1=5
        else:
            pcbx = 30  # v2=13, v1=30
            pcby = 30  # v2=13, v1=30
            pcbt = 1.6
            pcbpinr = 0.8  # v2=0.4, v1=0.8
            pcbr = 5  # corner fillet radius, v2=2, v1=5
        pcb = holder.faces("<Z").workplane(origin=(0, 0)).sketch().rect(pcbx, pcby).vertices().fillet(pcbr).finalize()
        pcb = cast(CQ, pcb)  # workaround for sketch.finalize() not returning the correct type
        pcb = pcb.extrude(pcbt, combine=False).findSolid()
        pcb = CQ(pcb).faces("<Z").workplane(origin=(0, 0)).add(pin_spots).circle(pcbpinr).extrude(pcbt + holder_base_height, combine="cut")

        # secondary bottom void to ensure spring pin solder doesn't get to the holder
        if version != "joe":
            pcb_bot_void2_d = 2
            offset_from_pcb = 1
            holder = holder.faces("<Z").workplane(origin=(0, 0)).sketch().rect(pcbx-offset_from_pcb, pcby-offset_from_pcb).vertices().fillet(pcbvr).finalize()
            holder = cast(CQ, holder)  # workaround for sketch.finalize() not returning the correct type
            holder = holder.cutBlind(-pcb_bot_void2_d)

        # pcb header pin holes
        if (version == "joe") or (version == "hoye12"):
            if version == "joe":
                hph_dia = 0.9  # header pin hole diameter
                hps = 2
                major_spacing = 4.8 + 0.3  # this accounts for the fact that the housing is 4.8 wide and the ramp sticks off an additional 0.3
                hpnx = 5
            elif version == "hoye12":
                hph_dia = 1  # header pin hole diameter
                hps = 2.54
                hpnx = 8
        else:
            hph_dia = 1  # header pin hole diameter
            hps = 2.54
            hpnx = 6
            major_spacing = 10.16  # this accounts for the fact that the housing is 4.8 wide and the ramp sticks off an additional 0.3

        if version == "hoye12":
            pcb = pcb.faces("<Z").workplane(origin=(0, 0)).rarray(hps, hps, hpnx, 2).circle(hph_dia / 2).extrude(-pcbt, combine="cut")
        else:
            pcb = pcb.faces("<Z").workplane(origin=(0, 0)).center(0, +major_spacing / 2).rarray(hps, hps, hpnx, 2).circle(hph_dia / 2).extrude(-pcbt, combine="cut")
            pcb = pcb.faces("<Z").workplane(origin=(0, 0)).center(0, -major_spacing / 2).rarray(hps, hps, hpnx, 2).circle(hph_dia / 2).extrude(-pcbt, combine="cut")

        if not no_threads:
            if (version == "joe") or (version == "hoye12"):
                if version == "joe":
                    # add in the pin header and connector stack, for use with cable assembly part number 2185091101
                    header_stack = u.import_step(components_dir / "877581017+511101060.stp").findSolid().translate((0, 0, -1.5))
                    hardware.add(header_stack.located(cq.Location((0, +major_spacing / 2, -holder_base_height - pcbt))))
                    hardware.add(header_stack.located(cq.Location((0, -major_spacing / 2, -holder_base_height - pcbt))))
                elif version == "hoye12":
                    header_stack = u.import_step(components_dir / "702461602.stp").findSolid().rotate((0, 0, 0), (1, 0, 0), -90).translate((0, 0, -5.71))
                    hardware.add(header_stack.located(cq.Location((0, 0, -holder_base_height - pcbt))))
            else:
                # add in the header and IDC connector stack
                header_stack = u.import_step(components_dir / "SFH213-PPPC-D06-ID-BK+HIF3FB-16DA-2.54DSA(71).step").findSolid().rotate((0, 0, 0), (1, 0, 0), -180)

                hardware.add(header_stack.located(cq.Location((0, +2 * 2.54, -holder_base_height - pcbt))))
                hardware.add(header_stack.located(cq.Location((0, -2 * 2.54, -holder_base_height - pcbt))))

        # pusher screw interface stuff here
        if (version == "joe") or (version == "hoye12"):
            bot_screw_len = 10
        # elif version == "yen":
        #    bot_screw_len = 25
        else:
            bot_screw_len = 15
        bot_screw = CounterSunkScrew(size="M6-1", fastener_type="iso14581", length=bot_screw_len, simple=no_threads)  # TODO: add pn

        c_flat_to_flat = 10
        c_flat_to_flat = c_flat_to_flat + 0.3  # add fudge factor so it can slide in
        c_diameter = c_flat_to_flat / (math.cos(math.tanh(1 / math.sqrt(3))))
        if (version == "joe") or (version == "hoye12"):
            coupler_len = 15
            coupler = u.import_step(components_dir / "Download_STEP_970150611 (rev1).stp").findSolid().translate((0, 0, -coupler_len / 2))
        else:
            coupler_len = 20
            coupler = u.import_step(components_dir / "Download_STEP_970200611 (rev1).stp").findSolid().translate((0, 0, -coupler_len / 2))

        if version == "yen":
            rarray_args = (pusher_mount_spacing, 1, 2, 1)
            dev1 = (-pusher_mount_spacing / 2, -walls_y / 4)
        else:
            rarray_args = (1, pusher_mount_spacing, 1, 2)
            dev1 = (-walls_x / 4, -pusher_mount_spacing / 2)
        hpc = holder
        holder = holder.faces(">Z").workplane(origin=(0, 0)).sketch().rarray(*rarray_args).rect(c_diameter, c_flat_to_flat).reset().vertices().fillet(c_diameter / 4).finalize().cutBlind(-coupler_len)
        holder = cast(CQ, holder)  # workaround for sketch.finalize() not returning the correct type
        mount_points = holder.faces(">Z").workplane(origin=(0, 0)).rarray(*rarray_args).vals()
        for mount_point in mount_points:
            hardware.add(coupler.located(cq.Location(mount_point.toTuple())))

        # this is cool, but it makes it too hard to solder the spring pins
        # if version == "yen":
        #    shroud_major = 9.6
        #    holder = holder.faces("<Z").wires().toPending().extrude(-shroud_major)
        #    holder = holder.faces("<Z").workplane(origin=(0, 0)).sketch().rect(pcbx, pcby).vertices().fillet(pcbr).offset(0.5).finalize().cutBlind(-shroud_major)

        holder = holder.faces("<Z").workplane(origin=(0, 0)).rarray(*rarray_args).clearanceHole(bot_screw, fit="Close", baseAssembly=hardware)

        if (version == "joe") or (version == "hoye12"):
            # extract the mounting hole negative
            mount_neg = hpc.cut(holder).translate((0,pusher_mount_spacing/2,-void_depth)).findSolid().Solids()[0]
        else:
            mount_neg = CQ()

        # put in a device 1 indicator
        holder = holder.faces(">Z").workplane(origin=dev1).circle(2).cutBlind(-0.5)

        out = {"holder": holder.findSolid()}
        out["pusher"] = pusher.findSolid()
        out["pcb"] = pcb
        out["hardware"] = hardware
        out["cv_print"] = cv_print
        out["mnt_print"] = mount_neg
        out["pusher_win"] = pusher_win

        return out

    # make the pieces
    holder_parts = mk_single_holder(drawings=drawings, components_dir=wrk_dir / "components")
    holder = holder_parts["holder"]
    # pin_holder = holder_parts["pin_holder"]
    pusher = holder_parts["pusher"]
    pcb = holder_parts["pcb"]
    holder_hw = holder_parts["hardware"]

    wp_single = CQ(holder)

    # mod the 1x1 holder with bottom shrouds
    if (version == "joe") or (version == "hoye12"):
        shroud_width = 3.5  # sum of both together, v2=3.5, v1=4
    else:
        shroud_width = 4  # sum of both together, v2=3.5, v1=4
    shroud_height = 25
    holder1x1 = CQ(holder).faces("<Z").wires().toPending().extrude(-shroud_height)
    holder1x1 = holder1x1.edges("|Z and >X").fillet(fil_major)  # must do this now because it will crash later
    bb1x1 = holder1x1.findSolid().BoundingBox()
    xlen1 = bb1x1.xlen
    ylen1 = bb1x1.ylen
    holder1x1 = holder1x1.faces("<Z").workplane(origin=(0, 0)).rect(xlen1 - 2 * shroud_width, ylen1).cutBlind(-shroud_height).findSolid()
    flange_bit, flange_hardware = mk_flange_bit(drawings=drawings, components_dir=wrk_dir / "components", flange_base_height=flange_base_height, thickness=flange_bit_thickness, whole_width=ylen1)

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
    wp_1x1 = wp_1x1.faces(">X").workplane(origin=(0, 0)).center(0, bb1x1.zmin + flange_bit_thickness / 2 + shroud_height).sketch().rect(flat_to_flat, side_nut.nut_diameter, angle=90).reset().vertices().fillet(side_nut.nut_diameter / 4).finalize().cutBlind(-side_nut.nut_thickness * 2)
    wp_1x1 = cast(CQ, wp_1x1)  # workaround for sketch.clearanceHole() not returning the correct type

    # put a side mounting m4 in the single holder for henry or hoye12
    if (version == "snaith") or (version == "hoye12"):
        if version == "snaith":
            side_screw2_len = 45
        elif version == "hoye12":
            side_screw2_len = 25
        side_nut_pocket_depth = 5  # max thickness for an M4 DIN985 nyloc nut
        side_screw2 = CounterSunkScrew(size="M4-0.7", fastener_type="iso14581", length=side_screw2_len, simple=no_threads)  # SHK-M4-45-V2-A2
        wp_single = wp_single.faces("<X").workplane(**u.cobb).clearanceHole(side_screw2, fit="Close", baseAssembly=hardware_single)
        wp_single = wp_single.faces(">X").workplane(**u.cobb, offset=-side_nut_pocket_depth).clearanceHole(fastener=side_nut, fit="Close", counterSunk=False, baseAssembly=hardware_single)
        wp_single = cast(CQ, wp_single)  # workaround for sketch.clearanceHole() not returning the correct type
        wp_single = wp_single.faces(">X").workplane(**u.cobb).sketch().rect(flat_to_flat, side_nut.nut_diameter, angle=90).reset().vertices().fillet(side_nut.nut_diameter / 4).finalize().cutBlind(-side_nut_pocket_depth)
        wp_single = cast(CQ, wp_single)  # workaround for sketch.clearanceHole() not returning the correct type

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
    wp_single = wp_single.edges("|Z and (<Y or >Y)").fillet(fil_major)
    wp_single = wp_single.faces(">Z").edges("<Y").chamfer(chamf_major)

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
    cv_print = cq.Assembly(holder_parts["cv_print"], name="cv_print")
    mnt_print = cq.Assembly(holder_parts["mnt_print"], name="mnt_print")
    pusher_win = cq.Assembly(holder_parts["pusher_win"], name="pusher_win")
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

    asys = cast(dict[str, dict[str, cq.Assembly]], {})
    asys["hoye_2x1"] = {"assembly": hoye_2x1}
    asys["hoye_1x1"] = {"assembly": hoye_1x1}
    asys["1x1"] = {"assembly": onex1}
    asys["2x2"] = {"assembly": twox2}
    asys["cv_print"] = {"assembly": cv_print}
    asys["mnt_print"] = {"assembly": mnt_print}
    asys["pusher_win"] = {"assembly": pusher_win}

    if "show_object" in globals():  # we're in cq-editor

        def lshow_object(*args, **kwargs):
            return show_object(*args, **kwargs)

    else:
        lshow_object = None

    TwoDToThreeD.outputter(asys, wrk_dir, save_steps=True, save_stls=False, show_object=lshow_object)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
