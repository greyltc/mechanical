#!/usr/bin/env python3
import cadquery as cq
import geometrics.toolbox as tb
import pathlib


class ScratchTool(object):
    extra_xy = 30
    glass_dim = 30
    bottom_z = 5
    glass_xy_fudge = 0.5;

    def __init__(self, extra_xy=30, glass_dim=30):
        self.extra_xy = extra_xy
        self.glass_dim = glass_dim

    def build(self):
        s = self
        assembly = []

        pocket_xy = s.glass_dim + s.glass_xy_fudge

        x = pocket_xy + s.extra_xy
        y = pocket_xy + s.extra_xy

        # make the spacer base layer
        bottom = cq.Workplane("XY")
        bottom = bottom.box(x, y, s.bottom_z, centered=(True, True, False))
        assembly.extend(bottom.vals())

        cpnd = cq.Compound.makeCompound(assembly)

        return cpnd


def make_demo_solids():
    s = ScratchTool(extra_xy=30, glass_dim=30)
    s = Sandwich(leng=166, wid=50, substrate_xy=30, cutout_spacing=35, endblock_width=12, aux_hole_spacing=16, block_offset_from_edge_of_base=1)
    cmpd = s.build()
    return cmpd.Solids()

def make_steps():
    salads = make_demo_solids()
    for salad in salads:
        this_hash = salad.hashCode()  # this might not be unique because it does not hash orientation
        tb.utilities.export_step(salad, pathlib.Path(f"{this_hash}.step"))

if "show_object" in locals():
    salads = make_demo_solids()
    for salad in salads:
        show_object(salad)
elif __name__ == "__main__":
    make_steps()
