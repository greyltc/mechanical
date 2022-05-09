#!/usr/bin/env python3
import cadquery as cq
import geometrics.toolbox as tb
import pathlib


def main():

    cutter_path = cq.Workplane("XY").rect(150, 150, centered=True).extrude(1).edges("|Z").fillet(10).faces("-Z").wires()

    demo_block = cq.Workplane("XY").rect(200, 200, centered=True).extrude(-5).edges("|Z").fillet(3)
    entry_point = [75, 0, 0]  # point along the path where the tool enters/exits

    # oring demo
    sweep_result, cutter_entry_shape = tb.groovy.mk_dovetail_ogroove(cutter_path, entry_point)
    oring_demo_block = demo_block.cut(sweep_result)
    oring_demo_block = oring_demo_block.cut(cutter_entry_shape.translate(entry_point))

    if "show_object" in globals():
        show_object(oring_demo_block)
    elif __name__ == "__main__":
        tb.utilities.export_step(oring_demo_block, pathlib.Path(f"groovy.step"))


main()
