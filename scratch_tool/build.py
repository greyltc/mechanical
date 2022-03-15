#!/usr/bin/env python3
import cadquery
from cadquery import CQ, cq
import geometrics.toolbox as tb
import pathlib

# engineering fit values used found from hints in
# https://www.trelleborg.com/en/seals/resources/design-support-and-engineering-tools/iso-fits-and-limits
# and
# https://de.misumi-ec.com/pdf/press/us_12e_pr1261.pdf
# dowel pins are d= 3 m6 12mm ones from RS 270-552 (15mm would be better)
# m6 shaft plus K7 hole ~= striking or cold press fit
# Minimum interference	=	-18  micrometer [µm]
# Maximum interference	=	-2  micrometer [µm]

# top = m6 shaft plus C9 hole ~= loose fit
# Minimum interference	=	52  micrometer [µm]
# Maximum interference	=	83  micrometer [µm]


class ScratchTool(object):
    extra_xy = 30
    glass_dim = 30

    dowel_ultra_clearance_d = 4

    dowel_nominal_d = 3
    dowel_largest_d = 3.012  # m6 class
    dowel_smallest_d = 3.02  # m6 class

    dowel_offset_from_center = 4.3306
    min_glass_pin_play = 0.2  # minimum play between a perfect 30.0 x 30.0 substrate and the dowel pins

    # cutting tool radius
    ctr = 2

    safe_step_xy = 28

    pedestal_xy = 45
    pedestal_z = 5

    dowel_xy_spacing = 40

    # bottom constants
    dowel_press_fudge_print_3d = 0.33
    bottom_z = 5

    glass_pocket_depth = 0.7
    glass_pocket_xy_pad = 0.3  # that's 0.1 larger than worst case glass size

    bottom_safe_step_z = 1
    final_safe_step_z = bottom_safe_step_z + glass_pocket_depth

    centerpunch_xy = 20

    # constants for top
    total_z = 15

    worst_case_glass_thickness = 2.2
    glass_thickness_margin = 0.3
    final_glass_thickness_margin = glass_thickness_margin - glass_pocket_depth

    glass_pocket_xy_fudge = 1
    pedistal_pocket_xy_fudge = 1

    dowel_clearance_fudge_print_3d = 0.7

    scratch_tool_width_o = 5.9  # for removing material from pixel pad zones
    scratch_tool_width_o_tc = 3  # for removing material from TC edge. 2.65 to edge of encap shelf, then a bit more
    scratch_tool_width_c = 2

    safe_step_z = 0.5

    guide_spacing_o = 17

    def __init__(self, extra_xy=30, glass_dim=30):
        self.extra_xy = extra_xy
        self.glass_dim = glass_dim

    def make_bottom(self, x, y, print3d=True):
        s = self
        co = "CenterOfBoundBox"

        # calcs
        if print3d == True:
            dowel_press_hole_d = s.dowel_nominal_d + s.dowel_press_fudge_print_3d
        else:
            dowel_press_hole_d = s.dowel_nominal_d  # engineering drawing to indicate K7 hole for press fit with m6 dowel

        cq.Workplane.undercutRelief2D = tb.u.undercutRelief2D
        b = cq.CQ().box(x, y, s.bottom_z, centered=(True, True, False)).val().Solids()[0]
        b = cq.CQ().add(b).edges("|Z").fillet(2).val().Solids()[0]  # fillet side edges
        b = cq.CQ().add(b).faces("<Z[-1]").edges().chamfer(0.5).val().Solids()[0]  # chamfer bottom edges
        b = cq.CQ().add(b).faces(">Z[-1]").workplane().rect(s.pedestal_xy, s.pedestal_xy).extrude(s.pedestal_z).val().Solids()[0]  # extrude substrate pedistal
        b = cq.CQ().add(b).faces(">Z[-1]").workplane().undercutRelief2D(s.safe_step_xy, s.safe_step_xy, s.ctr).cutBlind(-s.final_safe_step_z).val().Solids()[0]  # cut tiny step under substrate
        b = cq.CQ().add(b).faces(">Z[-1]").workplane().undercutRelief2D(s.glass_dim+s.glass_pocket_xy_pad, s.glass_dim+s.glass_pocket_xy_pad, s.ctr).cutBlind(-s.glass_pocket_depth).val().Solids()[0]  # cut glass pocket
        b = cq.CQ().add(b).faces("<Z[-1]").workplane().pushPoints([[-s.dowel_xy_spacing/2,-s.dowel_xy_spacing/2]]).hole(dowel_press_hole_d).val().Solids()[0]  # cut press fit dowel pin holes, marked as K7
        b = cq.CQ().add(b).faces("<Z[-1]").workplane().pushPoints([[ s.dowel_xy_spacing/2,s.dowel_xy_spacing/2]]).hole(dowel_press_hole_d).val().Solids()[0]  # cut press fit dowel pin holes, marked as K7
        b = cq.CQ().add(b).faces("<Z[-1]").workplane().undercutRelief2D(s.centerpunch_xy, s.centerpunch_xy, s.ctr).cutThruAll().val().Solids()[0]  # cut window
        b = cq.CQ().add(b).faces(">Z[-1]").edges("<X").chamfer(0.7).val().Solids()[0]  # make rotation indicator

        bwp = cq.CQ().add(b)
        # bwp.faces("<Z[-2]").tag("bottom_mate")
        return bwp

    def make_top(self, x, y, print3d=True, has_center_slot=True, outer_slot_widths=1, slots_rotated=False):
        s = self
        co = "CenterOfBoundBox"
        po = "ProjectedOrigin"

        if slots_rotated == True:
            rot = 90
        else:
            rot = 0

        # calcs
        top_z = s.total_z - s.bottom_z
        glass_pocket_xy = s.glass_dim + s.glass_pocket_xy_fudge
        pedistal_pocket_xy = s.pedestal_xy + s.pedistal_pocket_xy_fudge

        if print3d == True:
            dowel_clearance_hole_d = s.dowel_nominal_d + s.dowel_clearance_fudge_print_3d
        else:
            dowel_clearance_hole_d = s.dowel_nominal_d  # engineering drawing to indicate C9 hole for clearance fit with m6 dowel
        thickness_remaining_under_slot = s.worst_case_glass_thickness + s.pedestal_z - s.glass_pocket_depth
        guide_array_spacing_o = s.guide_spacing_o + s.scratch_tool_width_o

        glass_edge_offset = (s.glass_dim+s.glass_pocket_xy_pad)/2

        cq.Workplane.undercutRelief2D = tb.u.undercutRelief2D
        t = cq.CQ().box(x, y, top_z, centered=(True, True, False)).val().Solids()[0]
        t = cq.CQ().add(t).edges("|Z").fillet(2).val().Solids()[0]  # fillet side edges
        t = cq.CQ().add(t).faces(">Z[-1]").edges().chamfer(0.5).val().Solids()[0]  # chamfer top edges
        t = cq.CQ().add(t).faces("<Z[-1]").workplane(centerOption=co).undercutRelief2D(pedistal_pocket_xy, pedistal_pocket_xy, s.ctr).cutBlind(-s.pedestal_z).val().Solids()[0]  # cut indent for pedistal
        t = cq.CQ().add(t).faces("<Z[-2]").workplane(centerOption=co).undercutRelief2D(glass_pocket_xy, glass_pocket_xy, s.ctr).cutBlind(-(s.worst_case_glass_thickness + s.final_glass_thickness_margin)).val().Solids()[0]  # cut pocket glass lives in
        t = cq.CQ().add(t).faces("<Z[-3]").workplane(centerOption=co).undercutRelief2D(s.safe_step_xy, s.safe_step_xy, s.ctr).cutBlind(-s.safe_step_z).val().Solids()[0]  # cut tiny step to protect device surface
        #t = cq.CQ().add(t).faces("<Z[-1]").workplane(centerOption=co).pushPoints([[-s.dowel_xy_spacing/2,-s.dowel_xy_spacing/2],[s.dowel_xy_spacing/2,s.dowel_xy_spacing/2]]).cskHole(s.dowel_ultra_clearance_d, 19, 90).val().Solids()[0]  # ultra clearance holes
        t = cq.CQ().add(t).faces("<Z[-1]").workplane(centerOption=co).pushPoints([[-s.dowel_xy_spacing/2,-s.dowel_xy_spacing/2]]).cskHole(dowel_clearance_hole_d, 15, 90).val().Solids()[0]  # clearance hole marked in drawing as "3C9"
        t = cq.CQ().add(t).faces("<Z[-1]").workplane(centerOption=co).pushPoints([[ s.dowel_xy_spacing/2, s.dowel_xy_spacing/2]]).cskHole(dowel_clearance_hole_d, 15, 90).val().Solids()[0]  # clearance slot-hole
        t = cq.CQ().add(t).faces("<Z[-1]").workplane(centerOption=co).pushPoints([[ s.dowel_xy_spacing/2, s.dowel_xy_spacing/2]]).slot2D(4,3,-45).cutThruAll().val().Solids()[0]  # clearance slot marked in drawing as "3C9"

        if has_center_slot == True:
            t = cq.CQ().add(t).faces(">Z[-1]").workplane(centerOption=po).transformed(rotate=(0, 0, rot)).rect(s.scratch_tool_width_c, y).cutBlind(-(top_z - thickness_remaining_under_slot)).val().Solids()[0]  # cut the central slot
        t = cq.CQ().add(t).faces(">Z[-1]").workplane(centerOption=po).transformed(rotate=(0, 0, rot)).move( glass_edge_offset-outer_slot_widths/2,0).rect(outer_slot_widths, y).cutBlind(-(top_z - thickness_remaining_under_slot)).val().Solids()[0]  # cut an outer slot
        t = cq.CQ().add(t).faces(">Z[-1]").workplane(centerOption=po).transformed(rotate=(0, 0, rot)).move(-glass_edge_offset+outer_slot_widths/2,0).rect(outer_slot_widths, y).cutBlind(-(top_z - thickness_remaining_under_slot)).val().Solids()[0]  # cut an outer slot
        

        twp = cq.CQ().add(t)
        # twp.faces("<Z[-1]").tag("top_mate")
        return twp

    def build(self, print3d=True):
        s = self
        asy = cadquery.Assembly()

        # global calcs
        x = s.glass_dim + s.extra_xy
        y = s.glass_dim + s.extra_xy

        # make the bottom piece
        bottom = self.make_bottom(x, y, print3d=print3d)
        asy.add(bottom, name="bottom", color=cadquery.Color("red"))

        # make the top pieces
        top1 = self.make_top(x, y, print3d=print3d, has_center_slot=True, outer_slot_widths=s.scratch_tool_width_o, slots_rotated=False)
        top2 = self.make_top(x, y, print3d=print3d, has_center_slot=False, outer_slot_widths=s.scratch_tool_width_o_tc, slots_rotated=True)
        asy.add(top1.translate((0, 0, s.pedestal_z)), name="top1", color=cadquery.Color("gray"))
        asy.add(top2.translate((0, 0, s.pedestal_z+20)), name="top2", color=cadquery.Color("gray"))

        # constrain assembly
        # asy.constrain("bottom?bottom_mate", "top?top_mate", "Point")

        # solve constraints
        # asy.solve()

        return asy


def main():
    s = ScratchTool(extra_xy=30, glass_dim=30)
    print_3d = False  # changes hole tolerances, use False for cnc fab
    asy = s.build(print_3d)

    if print_3d == True:
        file_note = "print"
    else:
        file_note = "cnc"

    if "show_object" in globals():
        # show_object(asy)
        for key, val in asy.traverse():
            shapes = val.shapes
            if shapes != []:
                c = cq.Compound.makeCompound(shapes)
                odict = {}
                if val.color is not None:
                    co = val.color.wrapped.GetRGB()
                    rgb = (co.Red(), co.Green(), co.Blue())
                    odict["color"] = rgb
                show_object(c.locate(val.loc), name=val.name, options=odict)

    elif __name__ == "__main__":
        # save step
        asy.save(f"scratcher_{file_note}.step")
        cadquery.exporters.assembly.exportCAF(asy, f"scratcher_{file_note}.std")

        save_indivitual_stls = False
        save_indivitual_steps = True
        save_indivitual_breps = False

        if (save_indivitual_stls == True) or (save_indivitual_steps == True) or (save_indivitual_breps == True):
            # loop through individual pieces
            for key, val in asy.traverse():
                shapes = val.shapes
                if shapes != []:
                    # make sure we're only taking one of whatever this is
                    this = val.obj.val()
                    if hasattr(this, "__iter__"):
                        one = next(val.obj.val().__iter__())
                    else:
                        one = this

                    # save as needed
                    if save_indivitual_stls == True:
                        cadquery.exporters.export(one, f"{val.name}_{file_note}.stl")
                    if save_indivitual_steps == True:
                        cadquery.exporters.export(one, f"{val.name}_{file_note}.step")
                    if save_indivitual_breps == True:
                        cq.Shape.exportBrep(one, f"{val.name}_{file_note}.brep")


main()