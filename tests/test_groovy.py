import unittest

# from geometrics import groovy

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

        with tempfile.TemporaryDirectory() as tmpdirname:
            print("created temporary directory", tmpdirname)

    def test_vgroove(self):
        # path should be a wire in XY plane at Z=0
        # the path the cutting tool will follow
        cutter_path = cq.Workplane("XY").rect(150, 150, centered=True).extrude(1).edges("|Z").fillet(10).faces("-Z").wires()
        demo_block = cq.Workplane("XY").rect(200, 200, centered=True).extrude(-5).edges("|Z").fillet(3)
        entry_point = [75, 0, 0]  # point along the path where the tool enters/exits

        # vslot
        depth = 4
        sweep_result = mk_vgroove(cutter_path, entry_point, depth)
        vsalad = demo_block.cut(sweep_result).findSolid()

        with tempfile.TemporaryDirectory() as tmpdirname:
            print("created temporary directory", tmpdirname)


# if ("show_object" in locals()) or (__name__ == "__main__"):

#     # oring demo
#     sweep_result, cutter_entry_shape = mk_dovetail_ogroove(cutter_path, entry_point)
#     oring_demo_block = demo_block.cut(sweep_result)
#     oring_demo_block = oring_demo_block.cut(cutter_entry_shape.translate(entry_point))
#     osalad = oring_demo_block.solids()

#     if "show_object" in locals():  # only for running standalone in cq-editor
#         show_object(osalad)
#         show_object(vsalad)
#     elif __name__ == "__main__":
#         u.export_step(osalad, pathlib.Path("osalad.step"))
#         u.export_step(vsalad, pathlib.Path("vsalad.step"))
