#!/usr/bin/env python3
import cadquery
from cadquery import CQ, cq
from geometrics import toolbox as tb
#import geometrics.toolbox as tb
import pathlib

class LaserLabelHolder(object):
    name="tray"
    # units are mm
    x_nom = 30  # nominal substrate x dim
    y_nom = 30  # nominal substrate y dim
    xy_extra = 0.2  # add this to substrate x&y dims to find pocket size
    x_spacing = 2
    y_spacing = 2
    shelf_height = 3  # to raise the lower substrate surface this much off the bed
    wall_height = 0.75  # height of wall between substrates

    cut_tool_diameter = 5  # assume a round cutting tool with this diameter

    tweezer_allowance_depth = 0.5  # tweezer wells should go this far below the bottom of the substrate


    def __init__(self):
        pass
    
    def make_thing(self, nx=5, ny=5):
        s = self
        co = "CenterOfBoundBox"

        x_len = nx*(s.x_nom+s.xy_extra+s.x_spacing)
        y_len = ny*(s.y_nom+s.xy_extra+s.y_spacing)
        z_len = s.shelf_height + s.wall_height

        h00 = CQ().box(x_len, y_len, z_len, centered=(True, True, False))
        h01 = h00.workplane(centerOption=co).rarray(x_len/nx, y_len/ny, nx, ny, center=True).rect(3,3,centered=True).cutThruAll()

        return h01

    def build(self, nx=5, ny =5):
        asy = cadquery.Assembly()

        # make the bottom piece
        thing = self.make_thing(nx=nx, ny=ny)
        asy.add(thing, name="tray", color=cadquery.Color("gray"))

        return asy

def main():
    t = LaserLabelHolder()
    number_x = 5
    number_y = 5
    asy = t.build(nx=number_x, ny=number_y)

    print_3d = False  # changes hole tolerances, use False for cnc fab
    if print_3d == True:
        file_note = 'print'
    else:
        file_note = 'cnc'
    
    if "show_object" in globals():
        #show_object(asy)
        for key, val in asy.traverse():
            shapes = val.shapes
            if shapes != []:
                c = cq.Compound.makeCompound(shapes)
                odict = {}
                if val.color is not None:
                    co = val.color.wrapped.GetRGB()
                    rgb = (co.Red(), co.Green(), co.Blue())
                    odict['color'] = rgb
                show_object(c.locate(val.loc), name=val.name, options=odict)

    elif __name__ == "__main__":
        # save step
        asy.save(f'{t.name}_{file_note}.step')
        cadquery.exporters.assembly.exportCAF(asy, f'{t.name}_{file_note}.std')

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
                    if hasattr(this, '__iter__'):
                        one = next(val.obj.val().__iter__())
                    else:
                        one = this

                    # save as needed
                    if save_indivitual_stls == True:
                        cadquery.exporters.export(one, f'{val.name}_{file_note}.stl')
                    if save_indivitual_steps == True:
                        cadquery.exporters.export(one, f'{val.name}_{file_note}.step')
                    if save_indivitual_breps == True:
                        cq.Shape.exportBrep(one, f'{val.name}_{file_note}.brep')

main()