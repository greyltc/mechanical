#!/usr/bin/env python3
import cadquery as cq
import geometrics.toolbox as tb
import pathlib


class ScratchTool(object):
    extra_xy = 30
    glass_dim = 30
    bottom_z = 10
    glass_xy_fudge = 0.5

    dowel_nominal_d = 3
    dowel_press_fudge = 0.35

    dowel_offset_from_center = 4.3306
    nominal_glass_pin_play = 0.2

    bottom_safe_step_z = 1
    bottom_safe_step_xy = 28

    centerpunch_xy = 20

    def __init__(self, extra_xy=30, glass_dim=30):
        self.extra_xy = extra_xy
        self.glass_dim = glass_dim

    def build(self):
        s = self
        assembly = []

        pocket_xy = s.glass_dim + s.glass_xy_fudge

        x = pocket_xy + s.extra_xy
        y = pocket_xy + s.extra_xy

        dowel_press_d = s.dowel_nominal_d + s.dowel_press_fudge

        # make the bottom piece
        bottom = cq.Workplane("XY")
        bottom = bottom.box(x, y, s.bottom_z, centered=(True, True, False))
        bottom = bottom.faces("<Z").workplane(centerOption="CenterOfBoundBox").rarray(s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2*s.dowel_offset_from_center, 2, 2).hole(dowel_press_d)
        bottom = bottom.faces("<Z").workplane(centerOption="CenterOfBoundBox").rarray(2*s.dowel_offset_from_center, s.glass_dim+s.dowel_nominal_d+s.nominal_glass_pin_play, 2, 2).hole(dowel_press_d)
        bottom = bottom.faces(">Z").rect(s.bottom_safe_step_xy, s.bottom_safe_step_xy).cutBlind(s.bottom_safe_step_z)
        bottom = bottom.faces(">Z").rect(s.centerpunch_xy, s.centerpunch_xy).cutThruAll()

        assembly.extend(bottom.vals())

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
