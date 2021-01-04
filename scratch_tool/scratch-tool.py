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

    def build(self):
        s = self
        assembly = []

        # calcs for bottom
        x = s.glass_dim + s.extra_xy
        y = s.glass_dim + s.extra_xy
        dowel_press_d = s.dowel_nominal_d + s.dowel_press_fudge

        # calcs for top
        top_z = s.total_z - s.bottom_z
        glass_pocket_xy = s.glass_dim + s.glass_pocket_xy_fudge
        pedistal_pocket_xy = s.pedestal_xy + s.pedistal_pocket_xy_fudge
        center_lane_width = s.scratch_tool_width + s.scratch_tool_width_fudge
        dowel_clearance_d = s.dowel_nominal_d + s.dowel_clearance_fudge
        thickness_remaining_under_slot = s.worst_case_glass_thickness + s.pedestal_z
        outer_guide_array_spacing = s.outer_guide_spacing + center_lane_width

        # make the bottom piece
        bottom = cq.Workplane("XY")
        bottom = bottom.box(x, y, s.bottom_z, centered=(True, True, False))
        bottom = bottom.faces(">Z").workplane(centerOption="CenterOfBoundBox").rect(s.pedestal_xy, s.pedestal_xy).extrude(s.pedestal_z)
        bottom = bottom.faces(">Z").workplane(centerOption="CenterOfBoundBox").rect(s.safe_step_xy, s.safe_step_xy).cutBlind(-s.bottom_safe_step_z)
        bottom = bottom.faces("<Z").workplane(centerOption="CenterOfBoundBox").rarray(s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2*s.dowel_offset_from_center, 2, 2).hole(dowel_press_d)
        bottom = bottom.faces("<Z").workplane(centerOption="CenterOfBoundBox").rarray(2*s.dowel_offset_from_center, s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2, 2).hole(dowel_press_d)
        bottom = bottom.faces("<Z").workplane(centerOption="CenterOfBoundBox").rect(s.centerpunch_xy, s.centerpunch_xy).cutThruAll()
        assembly.extend(bottom.vals())

        # make the top piece
        top = cq.Workplane("XY")
        top = top.box(x, y, top_z, centered=(True, True, False)).translate((0, 0, s.bottom_z))
        top = top.faces("<Z").   workplane(centerOption="CenterOfBoundBox").rect(pedistal_pocket_xy, pedistal_pocket_xy).cutBlind(-s.pedestal_z)
        top = top.faces("<Z[1]").workplane(centerOption="CenterOfBoundBox").rect(glass_pocket_xy, glass_pocket_xy).cutBlind(-s.worst_case_glass_thickness-s.glass_thickness_margin)
        top = top.faces(">Z[2]").workplane(centerOption="CenterOfBoundBox").rect(s.safe_step_xy, s.safe_step_xy).cutBlind(-s.safe_step_z)
        top = top.faces(">Z").   workplane(centerOption="CenterOfBoundBox").rarray(s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2*s.dowel_offset_from_center, 2, 2).hole(dowel_clearance_d)
        top = top.faces(">Z").   workplane(centerOption="CenterOfBoundBox").rarray(2*s.dowel_offset_from_center, s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2, 2).hole(dowel_clearance_d)
        top = top.faces(">Z").   workplane(centerOption="CenterOfBoundBox").rect(center_lane_width, y).cutBlind(-(top_z-thickness_remaining_under_slot))
        top = top.faces(">Z").   workplane(centerOption="CenterOfBoundBox").rarray(outer_guide_array_spacing, 1, 2, 1).rect(center_lane_width, y).cutBlind(-(top_z-thickness_remaining_under_slot))
        assembly.extend(top.vals())

        cpnd = cq.Compound.makeCompound(assembly)

        return cpnd

def make_demo_solids():
    s = ScratchTool(extra_xy=30, glass_dim=30)
    cmpd = s.build()
    return cmpd.Solids()

def make_ouputs():
    salads = make_demo_solids()
    for salad in salads:
        this_hash = salad.hashCode()  # this might not be unique because it does not hash orientation
        tb.utilities.export_step(salad, pathlib.Path(f"{this_hash}.step"))
        cq.exporters.export(salad,f"{this_hash}.stl")

if "show_object" in locals():
    salads = make_demo_solids()
    for salad in salads:
        show_object(salad)
elif __name__ == "__main__":
    make_ouputs()
