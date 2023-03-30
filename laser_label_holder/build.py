#!/usr/bin/env python3

import cadquery
from cadquery import CQ, cq
import geometrics.toolbox.utilities as tbutil
from geometrics.toolbox import twod_to_threed
import pathlib
import logging


class LaserLabelHolder(object):
    name = "tray"
    # units are mm
    x_nom = 30.0  # nominal substrate x dim
    y_nom = 30.0  # nominal substrate y dim
    xy_extra = 0.2  # add this to substrate x&y dims to find pocket size
    x_spacing = 2.8
    y_spacing = 2.8
    shelf_height = 10  # to raise the lower substrate surface this much off the bed (0.5 for C02 laser tray)
    wall_height = 0.75  # height of wall between substrates

    cut_tool_diameter = 5  # assume a round cutting tool with this diameter

    tweezer_allowance_depth = 0.5  # tweezer wells should go this far below the bottom of the substrate
    tweezer_allowance_width = 12  # width of tweezer slots

    support_plate_t = 15  # strengthening underplate

    hole_d = 20  # hole in underplate

    chamfer = 0.5

    def __init__(self):
        # setup logging
        self.lg = logging.getLogger(__name__)
        self.lg.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        logFormat = logging.Formatter(("%(asctime)s|%(name)s|%(levelname)s|%(message)s"))
        ch.setFormatter(logFormat)
        self.lg.addHandler(ch)

    def make_thing(self, nx=5, ny=5):
        s = self
        co = "CenterOfBoundBox"
        fudge = 1

        unit_x = s.x_nom + s.xy_extra + s.x_spacing
        unit_y = s.y_nom + s.xy_extra + s.y_spacing

        x_len = nx * unit_x
        y_len = ny * unit_y
        z_len = s.shelf_height + s.wall_height

        one_void = CQ().box(s.x_nom + s.xy_extra, s.y_nom + s.xy_extra, s.shelf_height, centered=(True, True, False)).edges("|Z").fillet(s.cut_tool_diameter / 2)
        tweezer_void = CQ().box(unit_x + fudge, s.tweezer_allowance_width, s.wall_height + s.tweezer_allowance_depth, centered=(True, True, False))
        fatten_up = CQ().box(x_len, y_len, s.support_plate_t, centered=(True, True, False)).rarray(x_len / nx, y_len / ny, nx, ny, center=True).circle(s.hole_d / 2).cutThruAll().edges("not %Line").chamfer(s.chamfer)

        CQ.undercutRelief2D = tbutil.undercutRelief2D
        h00 = CQ().box(x_len, y_len, z_len, centered=(True, True, False))  # limits box

        h01 = h00.faces(">Z").workplane().rarray(x_len / nx, y_len / ny, nx, ny, center=True).undercutRelief2D(s.y_nom + s.xy_extra, s.y_nom + s.xy_extra, diameter=s.cut_tool_diameter).cutBlind(-s.wall_height)  # substrate pockets

        all_voids = h00.faces("<Z").workplane(invert=True).rarray(x_len / nx, y_len / ny, nx, ny, center=True).eachpoint(lambda l: one_void.val().located(l))  # voids under
        h02 = h01.cut(all_voids)

        tweezer_voids = h00.faces(">Z").workplane(invert=True).rarray(x_len / nx, y_len / ny, nx, ny, center=True).eachpoint(lambda l: tweezer_void.val().located(l))  # tweezer voids
        h03 = h02.cut(tweezer_voids)

        tweezer_voids2 = h00.faces(">Z").workplane(invert=True).rarray(x_len / nx, y_len / ny, nx, ny, center=True).eachpoint(lambda l: tweezer_void.rotate((0, 0, 0), (0, 0, 1), 90).val().located(l))  # tweezer voids
        h04 = h03.cut(tweezer_voids2)

        h05 = h04.union(fatten_up.translate((0, 0, -s.support_plate_t)))

        h06 = h05.faces("<Z").edges("%Line").chamfer(s.chamfer)

        return h06

    def build(self, nx=5, ny=5):
        asy = cadquery.Assembly()

        # make the bottom piece
        thing = self.make_thing(nx=nx, ny=ny)
        bb = thing.findSolid().BoundingBox()
        self.lg.debug(f"extents = ({bb.xlen},{bb.ylen},{bb.zlen})")
        asy.add(thing, name="tray", color=cadquery.Color("gray"))

        return asy


def main():
    try:
        wrk_dir = pathlib.Path(__file__).parent
    except Exception as e:
        wrk_dir = pathlib.Path.cwd()

    if "show_object" in globals():  # we're in cq-editor

        def lshow_object(*args, **kwargs):
            return show_object(*args, **kwargs)

    else:
        lshow_object = None

    t = LaserLabelHolder()
    number_x = 10  # 12 for C02 laser
    number_y = 10  # 9 for CO2 laser
    asy = t.build(nx=number_x, ny=number_y)

    built = {"plate": {"assembly": asy}}
    twod_to_threed.TwoDToThreeD.outputter(built, wrk_dir=wrk_dir, save_steps=False, save_stls=False, show_object=lshow_object)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
