#!/usr/bin/env python3
import cadquery
from cadquery import CQ, cq
import geometrics.toolbox as tb
import logging


class ChamberNG(object):
    # wall thicknesses
    wall = (5, 5, 10, 10)  # -X, +X, -Y, +Y (slots are in -Y wall)

    # nominal pcb thickness
    pcb_thickness = 1.6

    # (normal plane) clearance given around the crossbar PCBs when cutting their slots in the wall
    pcb_slot_clearance = pcb_thickness*0.10  # covers a PCB that's 10 percent too thick

    endblock_wall_spacing = 1  # from + and - Y walls
    endblock_thickness = 12

    # radius on the shelf fillet
    shelf_fr = 2

    # radius on the above shelf fillet
    above_shelf_fr = 10
    
    # extra room between the device plane and the walls on each side: (-X, +X, -Y, +Y)
    # these must be at least 0.7288 to prevent shadowing when spacing = 0 and shelf_height=5
    #x_minus = pcb_slot_clearance + pcb_thickness/2 # makes sense when spacing = 0
    #x_plus = pcb_slot_clearance + pcb_thickness/2 # makes sense when spacing = 0
    #x_minus = 0
    #x_plus = 0
    x_minus = above_shelf_fr
    x_plus = above_shelf_fr

    # these must be at least 2.5577 to prevent shadowing when yspacing = 0 and shelf_height=5
    y_minus = 3
    y_plus = 3
    extra = (x_minus, x_plus, y_minus, y_plus)

    # adds features on the sides of the shelves to ensure the PCBs get jammed up against their endblocks
    # only really makes sense when extra_x > 0 and x spacing = 0
    use_shelf_PCB_jammers = True

    pcb_height = 12
    wall_height = pcb_height + pcb_thickness/2+pcb_slot_clearance
    shelf_height = 5
    top_mid_height = 5

    # constants for the slot-side potting pocket
    potting_pocket_depth = 2
    potting_pocket_fillet = 2

    # potting groove offset from the three edges
    pg_offset = 2.5
    pg_depth = 1  #potting groove depth

    def __init__(self, array = (4, 1), subs =(30, 30), spacing=(10, 10)):
        self.array = array
        self.substrate_adapters = subs
        self.substrate_spacing = spacing

        self.period = (self.substrate_adapters[0]+self.substrate_spacing[0], self.substrate_adapters[1]+self.substrate_spacing[1])

        logging.basicConfig(format='%(message)s')
        self.log = logging.getLogger(__name__)

    def make_plane(self):
        """makes the plane where the devices will be"""
        s = self
        planex = s.array[0]*(s.substrate_adapters[0]+s.substrate_spacing[0])
        planey = s.array[1]*(s.substrate_adapters[1]+s.substrate_spacing[1])
        werkplane = CQ().rect(planex, planey)
        return werkplane

    def make_middle(self, wp):
        s = self
        co = "CenterOfBoundBox"
        
        if (s.substrate_spacing[0]/2 + s.extra[0]) <  (2*self.pcb_slot_clearance + self.pcb_thickness)/2:
            s.log.warning('Slots will be cut into the inner -X wall')
        
        if (s.substrate_spacing[0]/2 + s.extra[1]) <  (2*self.pcb_slot_clearance + self.pcb_thickness)/2:
            s.log.warning('Slots will be cut into the inner +X wall')

        shelf_width = s.endblock_wall_spacing + s.endblock_thickness

        if self.use_shelf_PCB_jammers == False:
            # TODO
            pass
            #shelf_void_extents[0] = shelf_void_extents[0] + s.extra_x
        
        # werkplane face
        wpf = cq.Face.makeFromWires(wp.val())

        # to get the dims of the working array
        wpbb = wpf.BoundingBox()  

        # the void under the device array
        av = wp.extrude(-s.wall_height)

        # the void under the device array plus the extra spacing values
        av_ex = CQ(av.findSolid())
        # need the if checks because extrude(0) chrashes
        if s.extra[0] > 0:  # add in -X direction
            av_ex = CQ(av_ex.findSolid()).faces("<X[-1]").wires().toPending().workplane().extrude(s.extra[0])
        if s.extra[1] > 0:  # add in -X direction
            av_ex = CQ(av_ex.findSolid()).faces(">X[-1]").wires().toPending().workplane().extrude(s.extra[1])
        if s.extra[2] > 0:  # add in -X direction
            av_ex = CQ(av_ex.findSolid()).faces("<Y[-1]").wires().toPending().workplane().extrude(s.extra[2])
        if s.extra[3] > 0:  # add in -X direction
            av_ex = CQ(av_ex.findSolid()).faces(">Y[-1]").wires().toPending().workplane().extrude(s.extra[3])
        av_ex_rect = av_ex.faces(">Z[-1]").wires()  # the rectangle for that

        # the void under the device array plus the extra spacing values plus the shelf space
        av_ex_s = (
            CQ(av_ex.findSolid())
            .faces("<Y[-1]").wires().toPending().workplane().extrude(shelf_width)  # add in -Y direction
            .faces(">Y[-1]").wires().toPending().workplane().extrude(shelf_width)  # add in +Y direction
        )

        # the ring extents box, including the shelves
        extents_box = (
            CQ(av_ex_s.findSolid())
            # the extra for the walls
            .faces("<X[-1]").wires().toPending().workplane().extrude(s.wall[0])  # add in -X direction
            .faces(">X[-1]").wires().toPending().workplane().extrude(s.wall[1])  # add in +X direction
            .faces("<Y[-1]").wires().toPending().workplane().extrude(s.wall[2])  # add in -Y direction
            .faces(">Y[-1]").wires().toPending().workplane().extrude(s.wall[3])  # add in +Y direction
            # add the shelf chunk
            .faces("<Z[-1]").wires().toPending().workplane().extrude(s.shelf_height)  # add in -Z direction
        )

        # cut the void above the shelf, then cut the extended window to make the shelved ring shape
        shelved_ring = (
            extents_box.cut(av_ex_s)
            .add(av_ex_rect).toPending().cutThruAll()
        )

        # non-slot side shelf mounting block holes
        shelved_ring = (
            shelved_ring.faces('+Z').faces('>Y').workplane(centerOption=co, invert=True, offset=s.shelf_height)
            .center((s.extra[0]-s.extra[1])/2, +shelf_width/2-s.endblock_thickness/2)  # invert=True flips Y but not X
            .rarray(xSpacing=(s.period[0]), ySpacing=1, xCount=s.array[0], yCount=1)
            .cskHole(**tb.c.csk('m5', 11))
        )

        # slot side shelf mounting block holes
        shelved_ring = (
            shelved_ring.faces('+Z').faces('<Y').workplane(centerOption=co, invert=True, offset=s.shelf_height)
            .center((s.extra[0]-s.extra[1])/2, -shelf_width/2+s.endblock_thickness/2)  # invert=True flips Y but not X
            .rarray(xSpacing=(s.period[0]), ySpacing=1, xCount=s.array[0], yCount=1)
            .cskHole(**tb.c.csk('m5', 11))
        )

        # add on the material for the top-mid piece
        shelved_ring = (
            CQ(shelved_ring.findSolid())
            .faces(">Z[-1]").wires().toPending().extrude(s.top_mid_height)  # add in +Z direction
        )

        # fillet the inner shelf corners
        shelved_ring = CQ().add(shelved_ring).edges('|Z and <Z[-1]').fillet(s.shelf_fr)

        # fillet the innter corners above the shelf
        shelved_ring = CQ().add(shelved_ring).edges('|Z and >Z[-1]').fillet(s.above_shelf_fr)

        # form PCB slot cutters
        c_len = wpbb.ylen + 2*shelf_width + s.extra[2] + s.extra[3] + s.wall[2] + s.wall[3]  # length of the slot cutter
        _pcb_slot_void = (
            CQ()
            .workplane(offset=-s.pcb_height)
            .rarray(xSpacing=(s.period[0]), ySpacing=1, xCount=s.array[0], yCount=1)
            .box(s.pcb_thickness+2*s.pcb_slot_clearance, c_len, s.pcb_height, centered=[True, False, False])
            .faces("<Y[-1]").workplane().circle(s.pcb_thickness/2+s.pcb_slot_clearance).extrude(-c_len)
            .translate([0, -c_len+wpbb.ymax+s.extra[3]+s.endblock_thickness, 0]) # so that the slots are cut in the -Y wall
        )

        # cut the PCB slots
        shelved_ring = (
            CQ(shelved_ring.findSolid())
            .cut(_pcb_slot_void.translate([-s.substrate_adapters[0]/2,0,0]))
            .cut(_pcb_slot_void.translate([ s.substrate_adapters[0]/2,0,0]))
        )

        # the side potting pocket
        side_pot_cutter = (
            CQ()
            .box(wpbb.xlen+2*s.potting_pocket_fillet+s.pcb_thickness+2*s.pcb_slot_clearance, 4*s.potting_pocket_depth, s.wall_height+2*s.potting_pocket_fillet, centered=[True, False, False])
            .translate([0, -4*s.potting_pocket_depth+wpbb.ymin-s.extra[2]-shelf_width-s.wall[2]+s.potting_pocket_depth, -s.wall_height-s.potting_pocket_fillet])
            #.edges().fillet(s.potting_pocket_fillet)
            #.edges().chamfer(s.potting_pocket_fillet)
        )
        shelved_ring = shelved_ring.cut(side_pot_cutter)

        # now cut the vgroove bevels in the side potting pocket
        spcbb = side_pot_cutter.findSolid().BoundingBox()
        svg = tb.groovy.mk_vgroove(CQ().rect(spcbb.xlen, spcbb.zlen, centered=False), (0,spcbb.zlen/2,0), s.potting_pocket_depth)
        svg = svg.translate((-spcbb.xlen/2, -spcbb.zlen, 0))
        svg = svg.rotate((0,0,0), (1,0,0), 90)
        srbb = shelved_ring.findSolid().BoundingBox()
        svg = svg.translate((0,srbb.ymin,s.potting_pocket_fillet))
        shelved_ring = shelved_ring.cut(svg)

        # now cut the paths to the entry/exit
        cone = cq.Solid.makeCone(0,s.potting_pocket_depth, s.potting_pocket_depth, dir=cq.Vector(0,-1,0))
        cone_right = CQ('XZ').add(cone).translate((srbb.xmax-s.pg_offset,srbb.ymin+s.potting_pocket_depth,0)) # srbb.ymin-s.potting_pocket_depth
        cone_left = cone_right.mirror(mirrorPlane='YZ')
        shelved_ring = shelved_ring.cut(cone_right)
        shelved_ring = shelved_ring.cut(cone_left)
        btw_path = CQ("YZ").polyline([(0,0),(-s.potting_pocket_depth,-s.potting_pocket_depth),(-s.potting_pocket_depth,s.potting_pocket_depth)]).close().extrude(srbb.xlen-2*s.pg_offset).translate((srbb.xmin+s.pg_offset,srbb.ymin+s.potting_pocket_depth,0))
        shelved_ring = shelved_ring.cut(btw_path)

        # split the two pieces
        top = shelved_ring.faces('>Z[-1]').workplane(-s.top_mid_height).split(keepTop=True)
        middle = shelved_ring.faces('>Z[-1]').workplane(-s.top_mid_height).split(keepBottom=True)

        # now cut the v potting groove for the potting between the pieces
        path = CQ().polyline([(srbb.xmin+s.pg_offset, srbb.ymin), (srbb.xmin+s.pg_offset, srbb.ymax-s.pg_offset), (srbb.xmax-s.pg_offset, srbb.ymax-s.pg_offset), (srbb.xmax-s.pg_offset, srbb.ymin)])
        pg = tb.groovy.mk_vgroove(path, (srbb.xmin+s.pg_offset, srbb.ymin,0), s.pg_depth)
        middle = middle.cut(pg)

        return (middle, top)


    def build(self):
        s = self
        asy = cadquery.Assembly()

        # the device plane
        werkplane = self.make_plane()
        asy.add(werkplane, name="werkplane")

        # make the middle piece
        middle, top_mid= self.make_middle(werkplane)
        asy.add(middle, name="middle", color=cadquery.Color("orange"))
        asy.add(top_mid, name="top_mid", color=cadquery.Color("yellow"))

        # make the top piece
        #top = self.make_top(x, y)
        #asy.add(vg, name="vg")

        # constrain assembly
        #asy.constrain("bottom?bottom_mate", "top?top_mate", "Point")

        # solve constraints
        asy.solve()

        return asy

def main():
    s = ChamberNG(array=(1, 4), subs =(30, 30), spacing=(0, 10))
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
                cadquery.exporters.export(c, f'{val.name}.stl')

main()