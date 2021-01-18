#!/usr/bin/env python3
import cadquery as cq
import geometrics.toolbox as tb
import pathlib


class ScratchTool(object):
    extra_xy = 30
    glass_dim = 30

    dowel_nominal_d = 3

    dowel_offset_from_center = 4.3306
    nominal_glass_pin_play = 0.2
    
    safe_step_xy = 28

    pedestal_xy = 45
    pedestal_z = 5

    # bottom constants
    dowel_press_fudge = 0.33
    bottom_z = 5

    bottom_safe_step_z = 1

    centerpunch_xy = 20

    # constants for top
    total_z = 15

    worst_case_glass_thickness = 2.2
    glass_thickness_margin = 0.3

    glass_pocket_xy_fudge = 1
    pedistal_pocket_xy_fudge = 1

    dowel_clearance_fudge = 0.7

    scratch_tool_width = 1
    scratch_tool_width_fudge = 1

    safe_step_z = 0.5

    outer_guide_spacing = 23

    def __init__(self, extra_xy=30, glass_dim=30):
        self.extra_xy = extra_xy
        self.glass_dim = glass_dim
    
    def make_bottom(self, x, y):
        s = self
        co = "CenterOfBoundBox"

        # calcs
        dowel_press_d = s.dowel_nominal_d + s.dowel_press_fudge

        b =                                               cq.CQ().box(x, y, s.bottom_z, centered=(True, True, False)).val().Solids()[0]
        b = cq.CQ().add(b).faces(">Z[-1]").workplane(centerOption=co).rect(s.pedestal_xy, s.pedestal_xy).extrude(s.pedestal_z).val().Solids()[0]  # extrude substrate pedistal
        b = cq.CQ().add(b).faces(">Z[-1]").workplane(centerOption=co).rect(s.safe_step_xy, s.safe_step_xy).cutBlind(-s.bottom_safe_step_z).val().Solids()[0]  # cut tiny step under substrate
        b = cq.CQ().add(b).faces("<Z[-1]").workplane(centerOption=co)                             .rarray(s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2*s.dowel_offset_from_center, 2, 2).hole(dowel_press_d).val().Solids()[0]  # cut press fit dowel pin holes
        b = cq.CQ().add(b).faces("<Z[-1]").workplane(centerOption=co).transformed(rotate=(0,0,90)).rarray(s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2*s.dowel_offset_from_center, 2, 2).hole(dowel_press_d).val().Solids()[0]  # cut press fit dowel pin holes
        b = cq.CQ().add(b).faces("<Z[-1]").workplane(centerOption=co).rect(s.centerpunch_xy, s.centerpunch_xy).cutThruAll().val().Solids()[0]  # cut window

        bwp = cq.CQ().add(b)
        bwp.faces("<Z[-2]").tag("bottom_mate")
        return bwp

    def make_top(self, x, y):
        s = self
        co = "CenterOfBoundBox"

        # calcs
        top_z = s.total_z - s.bottom_z
        glass_pocket_xy = s.glass_dim + s.glass_pocket_xy_fudge
        pedistal_pocket_xy = s.pedestal_xy + s.pedistal_pocket_xy_fudge
        center_lane_width = s.scratch_tool_width + s.scratch_tool_width_fudge
        dowel_clearance_d = s.dowel_nominal_d + s.dowel_clearance_fudge
        thickness_remaining_under_slot = s.worst_case_glass_thickness + s.pedestal_z
        outer_guide_array_spacing = s.outer_guide_spacing + center_lane_width

        t =                                                   cq.CQ().box(x, y, top_z, centered=(True, True, False)).val().Solids()[0]
        t = cq.CQ().add(t).faces("<Z[-1]").workplane(centerOption=co).rect(pedistal_pocket_xy, pedistal_pocket_xy).cutBlind(-s.pedestal_z).val().Solids()[0]  # cut indent for pedistal
        t = cq.CQ().add(t).faces("<Z[-2]").workplane(centerOption=co).rect(glass_pocket_xy, glass_pocket_xy).cutBlind(-(s.worst_case_glass_thickness+s.glass_thickness_margin)).val().Solids()[0]  # cut pocket glass lives in
        t = cq.CQ().add(t).faces("<Z[-3]").workplane(centerOption=co).rect(s.safe_step_xy, s.safe_step_xy).cutBlind(-s.safe_step_z).val().Solids()[0]  # cut tiny step to protect device surface
        t = cq.CQ().add(t).faces(">Z[-1]").workplane(centerOption=co)                             .rarray(s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2*s.dowel_offset_from_center, 2, 2).hole(dowel_clearance_d).val().Solids()[0]  # cut clearance fit dowel pin holes
        t = cq.CQ().add(t).faces(">Z[-1]").workplane(centerOption=co).transformed(rotate=(0,0,90)).rarray(s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2*s.dowel_offset_from_center, 2, 2).hole(dowel_clearance_d).val().Solids()[0]  # cut clearance fit dowel pin holes
        t = cq.CQ().add(t).faces(">Z[-1]").workplane(centerOption=co).rarray(outer_guide_array_spacing/2, 1, 3, 1).rect(center_lane_width, y).cutBlind(-(top_z-thickness_remaining_under_slot)).val().Solids()[0]  # cut the slots

        twp = cq.CQ().add(t)
        twp.faces("<Z[-1]").tag("top_mate")
        return twp

    def build(self):
        s = self
        asy = cq.Assembly()

        # global calcs
        x = s.glass_dim + s.extra_xy
        y = s.glass_dim + s.extra_xy

        # make the bottom piece
        bottom = self.make_bottom(x, y)
        asy.add(bottom, name="bottom", color=cq.Color("red"))


        # make the top piece
        top = self.make_top(x, y)
        asy.add(top, name="top")

        # constrain assembly
        asy.constrain("bottom?bottom_mate", "top?top_mate", "Point")

        # solve constraints
        asy.solve()

        return asy

def main():
    s = ScratchTool(extra_xy=30, glass_dim=30)
    asy = s.build()
    
    if "show_object" in globals():
        #show_object(asy)
        for key, val in asy.traverse():
            shapes = val.shapes
            if shapes != []:
                c = cq.Compound.makeCompound(shapes)
                odict = {}
                if val.color is not None:
                    co = val.color.wrapped.GetRGB()
                    rgb = (co.Red(), co.Green(), co.Blue())
                    odict['color'] = rgb
                show_object(c.locate(val.loc), name=val.name, options=odict)

    elif __name__ == "__main__":
        # save step
        asy.save('scratcher.step')

        # save STLs
        for key, val in asy.traverse():
            shapes = val.shapes
            if shapes != []:
                c = cq.Compound.makeCompound(shapes)
                cq.exporters.export(c, f'{val.name}.stl')

main()