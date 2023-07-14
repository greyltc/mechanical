#!/usr/bin/env python3

import cadquery as cq
from cadquery import CQ
from geometrics.toolbox.twod_to_threed import TwoDToThreeD
import geometrics.toolbox.utilities as u
from pathlib import Path
#from cq_warehouse.fastener import SocketHeadCapScrew, HexNut, SetScrew, CounterSunkScrew, HexNutWithFlange, CheeseHeadScrew, PanHeadScrew
#import cq_warehouse.extensions  # this does something even though it's not directly used
import math
from typing import cast

#setattr(cq.Workplane, "undercutRelief2D", u.undercutRelief2D)


def main():
    # set working directory
    try:
        wrk_dir = Path(__file__).parent
    except Exception as e:
        wrk_dir = Path.cwd()
    print(f"Working directory is {wrk_dir}")

    def assemble_box(components_dir) -> cq.Assembly:
        """box assembler"""
        asy = cq.Assembly()  # this being empty causes a warning on output

        box = u.import_step(components_dir / "1455NHD1601_plates_removed.stp")
        assert box
        box = box.translate((-1*(-5.385018+102.614983)/2, -1*(-75.409393-22.439394)/2, -85.440117))
        asy.add(box, name="enclosure")

        pcb = u.import_step(components_dir / "contact_checker.step")
        assert pcb
        pcb = pcb.rotate((0, 0, 0), (0, 1, 0), -90).rotate((0, 0, 0), (0, 0, 1), 90)
        pcb = pcb.translate((0, -9.69, 0))
        asy.add(pcb, name="pcb")

        return asy

    # assemble the box
    box_asy = assemble_box(components_dir=wrk_dir / "components")

    asys = cast(dict[str,dict[str, cq.Assembly]], {})
    asys["contact_checker"] = {"assembly": box_asy}

    if "show_object" in globals():  # we're in cq-editor

        def lshow_object(*args, **kwargs):
            return show_object(*args, **kwargs)

    else:
        lshow_object = None

    TwoDToThreeD.outputter(asys, wrk_dir, save_steps=False, save_stls=False, show_object=lshow_object)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
