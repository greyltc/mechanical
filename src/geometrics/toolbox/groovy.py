#!/usr/bin/env python3
import cadquery
from cadquery import cq, CQ
import math
import pathlib
import copy
from . import utilities as u


def mk_vgroove(cutter_path, depth):
    """for cutting grooves with a 90 degree countersink cutter"""
    cp_tangent = cutter_path.tangentAt()  # tangent to cutter_path
    cp_start = cutter_path.startPoint()
    build_plane = cq.Plane(origin=cp_start, normal=cp_tangent)
    half_profile = CQ(build_plane).polyline([(0, 0), (-depth, 0), (0, depth)]).close()
    cutter = half_profile.revolve(axisEnd=(1, 0, 0))
    cutter_split = cutter.split(keepTop=True)
    cutter_crosssection = cutter_split.faces("|X").wires().val()

    # start_point = cutter_path.wires().val().startPoint()
    # cutter_crosssection_shift = CQ(cutter_crosssection).translate(cp_start)

    to_sweep = CQ(cutter_crosssection).wires().toPending()
    sweep_result = to_sweep.sweep(cutter_path, combine=True, transition="round", isFrenet=True)
    return sweep_result


def mk_ogroove(cutter_path):
    print(2)


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
