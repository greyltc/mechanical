#!/usr/bin/env python3
from cadquery import cq, CQ
import math
import pathlib
import copy

# this boilerplate allows this module to be run directly as a script
if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    __package__ = "toolbox"
    from pathlib import Path
    import sys

    # get the dir that holds __package__ on the front of the search path
    print(__file__)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from . import utilities as u


def mk_vgroove(cutter_path, entry_point, depth):
    """for cutting grooves with a 90 degree countersink cutter"""
    half_profile = CQ("XZ").polyline([(0, 0), (depth, 0), (0, -depth)]).close()
    cutter = half_profile.revolve()
    cutter_split = cutter.split(keepTop=True)
    cutter_crosssection = cutter_split.faces("+Y")  # TODO do this more generally
    cutter_crosssection_shift = cutter_crosssection.translate(entry_point)

    to_sweep = cutter_crosssection_shift.wires().toPending()
    sweep_result = to_sweep.sweep(cutter_path, combine=True, transition="round", sweepAlongWires=False, isFrenet=True)
    return sweep_result


def mk_dovetail_ogroove(cutter_path, entry_point):
    """makes a very special oring grove"""
    # dims from https://web.archive.org/web/20210311103938/https://eicac.co.uk/O-Ring-Grooves for a 4mm oring
    grove_width = 3.10  # from sharp edges
    grove_depth = 3.20
    bottom_radius = 0.8  # R1
    top_radius = 0.25  # r2, the important one
    r = top_radius

    # industry standard?
    dovetail_angle = 66
    # use socahtoa to tell us how to draw  the sketch for the dovetail design
    a = grove_depth / math.sin(math.radians(dovetail_angle))
    b = (r + r / (math.sin(math.radians(90 - dovetail_angle)))) / math.tan(math.radians(dovetail_angle))
    p0 = (0, 0)
    p1 = (grove_width / 2, 0)
    p2 = (grove_width / 2 + a, -grove_depth)
    p3 = (0, -grove_depth)
    p1 = (grove_width / 2 + b, 0)
    p2 = (grove_width / 2 + b, -r)
    p3 = (grove_width / 2 + b - r * math.sin(math.radians(dovetail_angle)), -r - r * math.cos(math.radians(dovetail_angle)))
    p4 = (grove_width / 2 + a, -grove_depth)
    p5 = (0, -grove_depth)

    cutter_sketch_half = cq.Workplane("XZ").polyline([p0, p1, p2, p3, p4, p5]).close()
    cutter_sketch_revolved = cutter_sketch_half.revolve()
    ring_sketch = cq.Workplane("XZ").moveTo(p2[0], p2[1]).circle(r)
    ring = ring_sketch.revolve()
    cutter = cutter_sketch_revolved.cut(ring).faces("-Z").fillet(bottom_radius)

    # make shape for cutter entry/exit
    splitted = cutter.faces("-Z").workplane(-bottom_radius).split(keepTop=True, keepBottom=True)
    top = cq.Workplane(splitted.vals()[1]).translate([0, 0, grove_depth])
    bot = cq.Workplane(splitted.vals()[0]).faces("+Z").wires().toPending().extrude(grove_depth)

    cutter_entry_shape = bot.union(top)

    cutter_split = cutter.split(keepTop=True)
    cutter_crosssection = cutter_split.faces("+Y")  # TODO do this more generally
    cutter_crosssection_shift = cutter_crosssection.translate(entry_point)

    to_sweep = cutter_crosssection_shift.wires().toPending()
    sweep_result = to_sweep.sweep(cutter_path, combine=False)
    return sweep_result, cutter_entry_shape


if ("show_object" in locals()) or (__name__ == "__main__"):
    # path should be a wire in XY plane at Z=0
    # the path the cutting tool will follow
    cutter_path = cq.Workplane("XY").rect(150, 150, centered=True).extrude(1).edges("|Z").fillet(10).faces("-Z").wires()

    demo_block = cq.Workplane("XY").rect(200, 200, centered=True).extrude(-5).edges("|Z").fillet(3)
    entry_point = [75, 0, 0]  # point along the path where the tool enters/exits

    # vslot demo
    depth = 4
    sweep_result = mk_vgroove(cutter_path, entry_point, depth)
    vslot_demo_block = demo_block.cut(sweep_result)
    vsalad = vslot_demo_block.solids()

    # oring demo
    sweep_result, cutter_entry_shape = mk_ogroove(cutter_path, entry_point)
    oring_demo_block = demo_block.cut(sweep_result)
    oring_demo_block = oring_demo_block.cut(cutter_entry_shape.translate(entry_point))
    osalad = oring_demo_block.solids()

    if "show_object" in locals():  # only for running standalone in cq-editor
        show_object(osalad)
        show_object(vsalad)
    elif __name__ == "__main__":
        u.export_step(osalad, pathlib.Path("osalad.step"))
        u.export_step(vsalad, pathlib.Path("vsalad.step"))
