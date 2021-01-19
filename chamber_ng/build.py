#!/usr/bin/env python3
import cadquery as cq
from cadquery.cq import Workplane
import geometrics.toolbox as tb
import logging


class ChamberNG(object):
    # -X, +X, -Y, +Y (slots are in -Y wall)
    wall = (10, 10, 10, 10)
    pcb_thickness = 1.6

    # (normal plane) clearance given around the crossbar PCBs when cutting their slots in the wall
    pcb_slot_clearance = pcb_thickness*0.10/2  # covers a PCB that's 10 percent too thick

    # the height above the floor(shelf) that the endblocks hold the bottom edge of the crossbar PCBs
    #pcb_z_gap = 0.2

    # width of the hole in the wall
    #in_wall_void_width = 4
    #in_wall_void_extra_depth = 2  # further distance below shelf level

    endblock_wall_spacing = 1  # from + and - Y walls
    endblock_thickness = 12

    # add this much extra room in x and y
    # for x, at least 1.4576 is a requirement to prevent shadowing when spacing = 0 and shelf_height=5
    # for y, at least 5.1154 is a requirement to prevent shadowing when spacing = 0 and shelf_height=5 
    extra_x = (2*pcb_slot_clearance + pcb_thickness)  # makes sense when spacing = 0
    extra_y = 6

    # adds features on the sides of the shelves to ensure the PCBs get jammed up against their endblocks
    # only really makes sense when extra_x > 0 and x spacing = 0
    use_shelf_PCB_jammers = True

    wall_height = 12
    shelf_height = 5
    top_mid_height = 5

    # constants for the slot-side potting pocket
    potting_pocket_from_edges = [7+extra_x/2, 7+extra_x/2, top_mid_height-2, shelf_height-2]  # edge order: [+X, -X, +Z, -Z]
    potting_pocket_depth = 2
    potting_pocket_fillet = 2

    def __init__(self, array = (4,1), subs =(30, 30), spacing=(10, 10)):
        self.array = array
        self.substrate_adapters = subs
        self.substrate_spacing = spacing

        self.period = (self.substrate_adapters[0]+self.substrate_spacing[0], self.substrate_adapters[1]+self.substrate_spacing[1])

        logging.basicConfig(format='%(message)s')
        self.log = logging.getLogger(__name__)

    def make_middle(self):
        s = self
        co = "CenterOfBoundBox"
        extents = [
            s.wall[0]+s.wall[1]+s.substrate_spacing[0]+s.array[0]*(s.substrate_adapters[0]+s.substrate_spacing[0]) + s.extra_x,
            s.wall[2]+s.wall[3]+s.substrate_spacing[1]+s.array[1]*(s.substrate_adapters[1]+s.substrate_spacing[1])+2*(s.endblock_thickness+s.endblock_wall_spacing) + s.extra_y
        ]
        # if we're doing 100% packing in X, leave some room on the outside edges for screw heads and connectors
        if (s.substrate_spacing[0] == 0):
            if s.extra_x < (2*self.pcb_slot_clearance + self.pcb_thickness):
                s.log.warning('Slots will be cut into the side walls')

        shelf_width = s.endblock_wall_spacing+s.endblock_thickness

        mid_void_extents = [extents[0]-s.wall[0]-s.wall[1], extents[1]-s.wall[2]-s.wall[3]-2*shelf_width]
        shelf_void_extents = [extents[0]-s.wall[0]-s.wall[1]-s.extra_x, extents[1]-s.wall[2]-s.wall[3]]

        if self.use_shelf_PCB_jammers == False:
            shelf_void_extents[0] = shelf_void_extents[0] + s.extra_x


        # the base "ring"
        middle = (
            cq.Workplane('XY')
            .box(extents[0], extents[1], s.wall_height, centered=[True,True,False])
            .translate([(s.wall[1]-s.wall[0])/2,(s.wall[3]-s.wall[2])/2,0])
            .moveTo(0,0)
            .rect(mid_void_extents[0], mid_void_extents[1], centered=True)
            .cutThruAll()
            .moveTo(0,0)
            .rect(shelf_void_extents[0], shelf_void_extents[1], centered=True)
            .cutThruAll()
        )

        # add the shelf that holds the endblocks
        _shelf = (
            cq.Workplane('XY')
            .rect(extents[0], extents[1], centered=True)
            .extrude(-s.shelf_height)
            .translate([(s.wall[1]-s.wall[0])/2, (s.wall[3]-s.wall[2])/2,0])
            .moveTo(0,0)
            .rect(mid_void_extents[0], mid_void_extents[1], centered=True)
            .cutThruAll()
            )
        middle = middle.union(_shelf)

        # non-slot side shelf mounting block holes
        middle = (
            middle.faces('<Z')
            .workplane(origin=(0,0,4))
            .center(0, -mid_void_extents[1]/2-s.endblock_thickness/2)
            .rarray(xSpacing=(s.period[0]), ySpacing=1, xCount=s.array[0], yCount=1)
            .cskHole(**tb.c.csk('m5', 11))
        )

        # slot side shelf mounting block holes
        middle = (
            middle.faces('<Z')
            .workplane(origin=(0,0,4))
            .center(0, mid_void_extents[1]/2+s.endblock_thickness/2)
            .rarray(xSpacing=(s.period[0]), ySpacing=1, xCount=s.array[0], yCount=1)
            .cskHole(**tb.c.csk('m5', 11))
        )

        # the top-mid piece
        _top_mid = (
            cq.Workplane('XY')
            .rect(extents[0], extents[1], centered=True).extrude(s.top_mid_height)
            .translate([(s.wall[1]-s.wall[0])/2,(s.wall[3]-s.wall[2])/2, s.wall_height])
            .moveTo(0,0)
            .rect(extents[0]-s.wall[0]-s.wall[1], extents[1]-s.wall[2]-s.wall[3], centered=True)
            .cutThruAll()
        )
        middle = middle.union(_top_mid)

        # a construction tool for subtracting the PCB slots
        _pcb_slot_void = (
            cq.Workplane('XY')
            .rarray(xSpacing=(s.period[0]), ySpacing=1, xCount=s.array[0], yCount=1)
            .box(s.pcb_thickness+2*s.pcb_slot_clearance, extents[1], s.wall_height, centered=[True, False, False])
            .translate([0, -extents[1]+mid_void_extents[1]/2+shelf_width, 0]) # so that the slots are cut in the -Y wall
            )
        middle = middle.cut(_pcb_slot_void.translate([-s.substrate_adapters[0]/2,0,0]))
        middle = middle.cut(_pcb_slot_void.translate([ s.substrate_adapters[0]/2,0,0]))

        # make the slot side potting pocket
        _side_potting_pocket = (
            cq.Workplane('XY')
            .box(extents[0], extents[1], s.wall_height+s.shelf_height+s.top_mid_height, centered=[True, False, False])
            .translate([0, -extents[1]-mid_void_extents[1]/2-shelf_width-s.wall[2]+s.potting_pocket_depth, -s.shelf_height])
            .faces('>X[-1]').workplane(-s.potting_pocket_from_edges[0]).split(keepBottom=True)
            .faces('<X[-1]').workplane(-s.potting_pocket_from_edges[1]).split(keepBottom=True)
            .faces('>Z[-1]').workplane(-s.potting_pocket_from_edges[2]).split(keepBottom=True)
            .faces('<Z[-1]').workplane(-s.potting_pocket_from_edges[3]).split(keepBottom=True)
            .edges().fillet(s.potting_pocket_fillet)
        )
        middle = middle.cut(_side_potting_pocket)
        #potting_pocket_from_edges = [2, 2, 2, 2]  # edge order: [+X, -X, +Z, -Z]

        top = middle.faces('>Z[-1]').workplane(-s.top_mid_height).split(keepTop=True)
        middle = middle.faces('>Z[-1]').workplane(-s.top_mid_height).split(keepBottom=True)


        return (middle, top)

        #middle = cq.Workplane('ZX').add(middle.findSolid()).faces('>Y').wires().toPending().extrude(8)


    def build(self):
        s = self
        asy = cq.Assembly()

        # make the middle piece
        middle, top_mid = self.make_middle()
        asy.add(middle, name="middle", color=cq.Color("orange"))
        asy.add(top_mid, name="top_mid", color=cq.Color("yellow"))


        # make the top piece
        #top = self.make_top(x, y)
        #asy.add(top, name="top")

        # constrain assembly
        #asy.constrain("bottom?bottom_mate", "top?top_mate", "Point")

        # solve constraints
        asy.solve()

        return asy

def main():
    s = ChamberNG(array=(1, 1), subs =(30, 30), spacing=(0, 0))
    asy = s.build()
    
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
        asy.save('chamber_ng.step')

        # save STLs
        for key, val in asy.traverse():
            shapes = val.shapes
            if shapes != []:
                c = cq.Compound.makeCompound(shapes)
                cq.exporters.export(c, f'{val.name}.stl')

main()