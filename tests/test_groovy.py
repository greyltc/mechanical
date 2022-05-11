import unittest
from geometrics.toolbox import groovy

from geometrics.toolbox import utilities as u

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

    def test_vgroove(self):
        # path should be a wire in XY plane at Z=0
        # the path the cutting tool will follow
        cq.Workplane.mk_vgroove = groovy.mk_vgroove  # add our vgroove function to the Workplane class
        cutter_path = cq.Workplane("XY").rect(150, 150, centered=True).extrude(1).edges("|Z").fillet(10).faces("-Z").wires().val()
        demo_block = cq.Workplane("XY").rect(200, 200, centered=True).extrude(-200).edges("|Z").fillet(3)

        # vslot
        depth = 4
        co = {"centerOption": "CenterOfBoundBox"}
        demo_block = demo_block.faces(">Z").workplane(**co).add(cutter_path).wires().toPending().mk_vgroove(depth)
        demo_block = demo_block.faces("<Z").workplane(**co).sketch().rect(50, 50).vertices().fillet(10).finalize().mk_vgroove(depth)
        demo_block = demo_block.faces("<X").workplane(**co).sketch().rarray(75, 75, 2, 2).circle(25).finalize().mk_vgroove(depth)

        tmpdirname = tempfile.mkdtemp()
        outfile = pathlib.Path(tmpdirname) / "vgroove.step"
        u.export_step(demo_block, outfile)
