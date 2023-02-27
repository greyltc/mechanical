#!/usr/bin/env python3

import cadquery
from cadquery import CQ, cq
import geometrics.toolbox.utilities as tbutil
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
    shelf_height = 3.25  # to raise the lower substrate surface this much off the bed
    wall_height = 0.75  # height of wall between substrates

    cut_tool_diameter = 5  # assume a round cutting tool with this diameter

    tweezer_allowance_depth = 0.5  # tweezer wells should go this far below the bottom of the substrate
    tweezer_allowance_width = 12  # width of tweezer slots

    support_plate_t = 5  # strengthening underplate

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

        offset_for_fatten_up = s.support_plate_t - z_len + s.tweezer_allowance_depth + s.wall_height

        one_void = CQ().box(s.x_nom + s.xy_extra, s.y_nom + s.xy_extra, s.shelf_height, centered=(True, True, False)).edges("|Z").fillet(s.cut_tool_diameter / 2)
        tweezer_void = CQ().box(unit_x + fudge, s.tweezer_allowance_width, s.wall_height + s.tweezer_allowance_depth, centered=(True, True, False))
        fatten_up = CQ().box(x_len, y_len, s.support_plate_t, centered=(True, True, False)).rarray(x_len / nx, y_len / ny, nx, ny, center=True).circle(s.hole_d / 2).cutThruAll().edges("not %Line").chamfer(s.chamfer)

        CQ.undercutRelief2D = tbutil.undercutRelief2D
        h00 = CQ().box(x_len, y_len, z_len, centered=(True, True, False))  # limits box
        # h01 = h00.faces('>Z').workplane().rarray(x_len/nx, y_len/ny, nx, ny, center=True).rect(unit_x+fudge, s.tweezer_allowance_width).cutBlind(-s.wall_height-s.tweezer_allowance_depth)  # x tweezer cuts
        # h02 = h01.faces('>Z').workplane().rarray(x_len/nx, y_len/ny, nx, ny, center=True).rect(s.tweezer_allowance_width, unit_y+fudge).cutBlind(-s.wall_height-s.tweezer_allowance_depth)  # y tweezer cuts
        h01 = h00.faces(">Z").workplane().rarray(x_len / nx, y_len / ny, nx, ny, center=True).undercutRelief2D(s.y_nom + s.xy_extra, s.y_nom + s.xy_extra, diameter=s.cut_tool_diameter).cutBlind(-s.wall_height)  # substrate pockets

        all_voids = h00.faces("<Z").workplane(invert=True).rarray(x_len / nx, y_len / ny, nx, ny, center=True).eachpoint(lambda l: one_void.val().located(l))  # voids under
        h02 = h01.cut(all_voids)

        tweezer_voids = h00.faces(">Z").workplane(invert=True).rarray(x_len / nx, y_len / ny, nx, ny, center=True).eachpoint(lambda l: tweezer_void.val().located(l))  # tweezer voids
        h03 = h02.cut(tweezer_voids)

        tweezer_voids2 = h00.faces(">Z").workplane(invert=True).rarray(x_len / nx, y_len / ny, nx, ny, center=True).eachpoint(lambda l: tweezer_void.rotate((0, 0, 0), (0, 0, 1), 90).val().located(l))  # tweezer voids
        h04 = h03.cut(tweezer_voids2)

        h05 = h04.translate((0, 0, offset_for_fatten_up)).union(fatten_up)

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
    t = LaserLabelHolder()
    number_x = 12
    number_y = 9
    asy = t.build(nx=number_x, ny=number_y)

    print_3d = False  # changes hole tolerances, use False for cnc fab
    if print_3d == True:
        file_note = "print"
    else:
        file_note = "cnc"

    if "show_object" in globals():
        # show_object(asy)
        for key, val in asy.traverse():
            shapes = val.shapes
            if shapes != []:
                c = cq.Compound.makeCompound(shapes)
                odict = {}
                if val.color is not None:
                    co = val.color.wrapped.GetRGB()
                    rgb = (co.Red(), co.Green(), co.Blue())
                    odict["color"] = rgb
                show_object(c.locate(val.loc), name=val.name, options=odict)

    elif __name__ == "__main__":
        # save step
        asy.save(f"{t.name}_{file_note}.step")
        cadquery.exporters.assembly.exportCAF(asy, f"{t.name}_{file_note}.std")

        save_indivitual_stls = False
        save_indivitual_steps = True
        save_indivitual_breps = False

        if (save_indivitual_stls == True) or (save_indivitual_steps == True) or (save_indivitual_breps == True):
            # loop through individual pieces
            for key, val in asy.traverse():
                shapes = val.shapes
                if shapes != []:
                    # make sure we're only taking one of whatever this is
                    this = val.obj.val()
                    if hasattr(this, "__iter__"):
                        one = next(val.obj.val().__iter__())
                    else:
                        one = this

                    # save as needed
                    if save_indivitual_stls == True:
                        cadquery.exporters.export(one, f"{val.name}_{file_note}.stl")
                    if save_indivitual_steps == True:
                        cadquery.exporters.export(one, f"{val.name}_{file_note}.step")
                    if save_indivitual_breps == True:
                        cq.Shape.exportBrep(one, f"{val.name}_{file_note}.brep")


main()
