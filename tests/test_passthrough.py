import unittest
from geometrics.toolbox import passthrough

from geometrics.toolbox import utilities as u

import cadquery
from cadquery import cq

import pathlib
import tempfile


class PassthroughTestCase(unittest.TestCase):
    """passthrough testing"""

    def test_passthrough(self):

        cq.Workplane.passthrough = passthrough.make_cut
        mwp = cq.Workplane("XZ").circle(80.0).extrude(20)
        mwp = mwp.translate((99, 99, 99))
        mwp = mwp.faces("<Y").workplane(centerOption="CenterOfBoundBox")
        mwp = mwp.rarray(30, 20, 2, 2).passthrough(rows=8, angle=80, kind="C")

        tmpdirname = tempfile.mkdtemp()
        outfile = pathlib.Path(tmpdirname) / "passthrough.step"
        u.export_step(mwp, outfile)

    def test_oringer(self):
        """testing for an o-ring based pcb passthrough"""
        cq.Workplane.make_oringer = passthrough.make_oringer
        wall_thickness = 12

        pt_pcb_width = 82.7
        outer_depth = 9.27
        inner_depth = 9.27

        mwp = cq.Workplane("ZX").circle(80.0).extrude(wall_thickness)
        mwp = mwp.translate((99, 99, 99))
        mwp = mwp.faces("<Y").workplane(centerOption="CenterOfBoundBox")

        hardware = cadquery.Assembly(name="passthrough hardware")
        pcb = cadquery.Assembly(name="passthrough pcbs")
        oringer = cadquery.Assembly(name="passthroughs")

        mwp = mwp.rarray(1, 40, 1, 3).make_oringer(board_width=pt_pcb_width, board_inner_depth=inner_depth, board_outer_depth=outer_depth, pt_asy=oringer, pcb_asy=pcb, hw_asy=hardware)

        final = cadquery.Assembly(name="passthrough testing")
        final.add(mwp, name="base part")
        final.add(hardware)
        final.add(pcb)
        final.add(oringer)

        tmpdirname = tempfile.mkdtemp()
        outfile = pathlib.Path(tmpdirname) / "passthrough.step"
        final.save(str(outfile))
