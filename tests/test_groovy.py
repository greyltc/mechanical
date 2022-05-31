import unittest
from geometrics.toolbox import groovy
import math

from geometrics.toolbox import utilities as u

import cadquery
from cadquery import cq

import pathlib
import tempfile


class GroovyTestCase(unittest.TestCase):
    """groovy testing"""

    def test_dovetail(self):
        # path should be a wire in XY plane at Z=0
        # the path the cutting tool will follow
        cutter_path = cq.Workplane("XY").rect(150, 150, centered=True).extrude(1).edges("|Z").fillet(10).faces("-Z").wires()

        demo_block = cq.Workplane("XY").rect(200, 200, centered=True).extrude(-5).edges("|Z").fillet(3)
        entry_point = [75, 0, 0]  # point along the path where the tool enters/exits

        sweep_result, cutter_entry_shape = groovy.mk_dovetail_ogroove(cutter_path, entry_point)

        result = demo_block.cut(sweep_result)
        result = result.cut(cutter_entry_shape.translate(entry_point))
        osalad = result.findSolid()

        tmpdirname = tempfile.mkdtemp()
        outfile = pathlib.Path(tmpdirname) / "dovetail.step"
        u.export_step(osalad, outfile)

    def test_groove(self):
        # path should be a wire in XY plane at Z=0
        # the path the cutting tool will follow
        cq.Workplane.mk_groove = groovy.mk_groove  # add our vgroove function to the Workplane class
        cutter_path = cq.Workplane("XY").rect(150, 150, centered=True).extrude(1).edges("|Z").fillet(10).faces("-Z").wires().val()
        demo_block = cq.Workplane("XY").rect(200, 200, centered=True).extrude(-200).edges("|Z").fillet(3)
        asy = cadquery.Assembly()

        depth = 4  # vslot
        ring_cs = 1  # o-ring cross-section diameter
        co = {"centerOption": "CenterOfBoundBox"}
        demo_block = demo_block.faces(">Z").workplane(**co).add(cutter_path).wires().toPending().mk_groove(vdepth=depth)
        demo_block = demo_block.faces("<Z").workplane(**co).sketch().rect(50, 50).vertices().fillet(10).finalize().mk_groove(vdepth=depth)

        demo_block = demo_block.faces("<X").workplane(**co).sketch().rarray(75, 75, 2, 2).circle(25).finalize().mk_groove(vdepth=depth)
        min_inner_rad = 3 * ring_cs
        gland_width = groovy.get_gland_width(ring_cs=ring_cs)
        mid_rad = min_inner_rad + gland_width / 2
        demo_block = demo_block.faces(">X").workplane(**co).sketch()
        demo_block = demo_block.push([(75 / 2, 75 / 2)]).rect(50, 50, angle=31).reset()
        demo_block = demo_block.push([(-75 / 2, -75 / 2)]).rect(50, 50, angle=7).reset()
        demo_block = demo_block.push([(75 / 2, -75 / 2)]).rect(50, 50, angle=23).reset()
        demo_block = demo_block.push([(-75 / 2, 75 / 2)]).rect(50, 50, angle=-17).reset()
        demo_block = demo_block.vertices().fillet(mid_rad).finalize().mk_groove(ring_cs=ring_cs, hardware=asy)

        demo_block = demo_block.faces("<Y").workplane(**co).mk_groove(ring_cs=ring_cs, follow_pending_wires=False, ring_id=90, gland_x=70, gland_y=100, hardware=asy)
        demo_block = demo_block.faces(">Y").workplane(**co).mk_groove(ring_cs=ring_cs, follow_pending_wires=False, ring_id=111, gland_x=80, gland_y=100, hardware=asy)

        tmpdirname = tempfile.mkdtemp()
        outfile = pathlib.Path(tmpdirname) / "groove.step"
        asy.add(demo_block)
        asy.save(str(outfile))  # save step
