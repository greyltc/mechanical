#!/usr/bin/env python3
import cadquery
from cadquery import CQ, cq
import geometrics.toolbox as tb
import logging
import math
import numpy as np


class ChamberNG(object):
    # wall thicknesses
    wall = (5, 5, 12, 12)  # -X, +X, -Y, +Y (slots are in -Y wall)

    # crossbar pcb shape parameters n
    pcb_thickness = 1.6  # nominally
    pcb_cut_rad = 2
    pcb_top_bump_up = 2.75  # gives room for a screw hole
    pcb_bottom_bump_down = 5 + 0.25  # gives room for a screw hole plus makes numbers height a round number
    pcb_min_height = 15  # anything smaller and I can't fit in all the wires
    pcb_bottom_bump_offset = 22  # offset from edge of PCB, needed to prevent shadowing from endblock extension
    pcb_mount_hole_offset = 3  # how far in x and y the mount hole centers are from their corners
    pcb_mount_hole_d = 2.2  # mount hole diameters
    pcb_external_connector_width = 2.54*6
    pcb_height = pcb_min_height + pcb_top_bump_up + pcb_bottom_bump_down # pcb height max
    pcb_alignment_hole_d = 3  # nominal for RS pn 374-020


    # subadapter pcb paramters
    #sa_pcb_thickness = 1
    #sa_pcb_border_thickness = (1.75, 1.75)  # (pin side, non-pin side)
    #sa_pf_hole_d = 0.5  # for pressfit pins (shaft nominal d = 0.457mm
    
    # substrate adapter parameters
    sa_spring_hole_d = 1.78  # spring pin mount hole diameter (pn 0921-1)
    sa_spring_hole_offset = 3.25  # from edge of board
    sa_socket_hole_d = 1.35  # pin socket mounting hole diameter (pn 5342)
    sa_border_thickness = (5.1, 3)  # defines the window border width (pin side, non-pin side)
    sa_spacing = 1.20  # distance between the adapter and the substrate surface
    # such that pin 0921-1 has the correct remaining travel when in use. nominally, this remaining travel
    # would be 0.5mm and that corresponds to a spacer thickness here of 1.26mm, but a 1.2mm thick PCB is a good option

    # aux connection parameters
    aux_con_pad_hole_d = 0.5  # for the holes cut in the adapter spacer pcb that cresspons to where the
    # auxiliary connection landing pads will be
    aux_con_pin_clearance_d = 1.9  # size of the holes needed to expose the aux pads

    # adapter spacer
    #as_thickness = pcb_thickness + 0.76  # 0.76 is the height of the shoulder of the millmax pressfit pins 

    # workplane offset from top of PCB
    woff = pcb_top_bump_up

    # (normal plane) clearance given around the crossbar PCBs when cutting their slots in the wall
    pcb_slot_clearance = pcb_thickness*0.10  # covers a PCB that's 10 percent too thick
    pcb_z_float = 0.25  # floats the PCB bottom off the shelf by this much

    endblock_wall_spacing = 0.5  # from + and - Y walls
    endblock_thickness_shelf = 12
    endblock_thickness_extension = 12+pcb_cut_rad
    endblock_screw_offset = 6  # distance from the endblock edge to clamp screw hole center
    endblock_thickness = endblock_thickness_shelf + endblock_thickness_extension
    eb_locknut_depth = 5
    eb_locknut_width = tb.c.std_hex_nuts["m5"]["flat_w"]
    eb_mount_hole_depth = 6  # threaded mount hole depth
    eb_mount_hole_tap_r = tb.c.std_screw_threads['m2']["tap_r"]  # for accu screw pn SSB-M2-6-A2
    pressfit_hole_d_nominal = 3  # alignment pin nominal dimension
    pressfit_hole_d = pressfit_hole_d_nominal - 0.035  # used in sizing the holes for endblock pressfits
    alignment_pin_clear_d = pressfit_hole_d_nominal + 0.45  # used in sizing holes in sandwich layers
    alignment_pin_slide_d = pressfit_hole_d_nominal + 0.15  # for the holes in the substrate holder layer
    spacer_h = 1.6  # for accu pn HPS-3.6-2.2-1.6-N
    pressfit_hole_depth = 10
    alignment_pin_spacing = 16
    pcb_alignment_hole_depth = 4.8  #  for RS pn 374-020, 8mm long

    # sandwich parameters
    sandwich_xbuffer = 1  # space to give between sandwich and chamber x walls on both sides
    sapd = 3  # nominal diameter for the substrate alignment pins
    sapd_press = sapd - 0.05  # no movement, alignment matters, used in crescent substrate holder layer
    #sapd_slide = sapd + 0.15  # needs movement, algnment matters
    sapd_clear = sapd + 0.45  # free movement, alignment does not matter
    sap_offset_fraction = 0.35  # fraction of the substrate dimension(up to 0.50) to offset the alignment pins to prevent device rotation
    tube_bore = 4.8  # for RS PRO silicone tubing stock number 667-8448
    tube_wall = 1.6  # for RS PRO silicone tubing stock number 667-8448
    tube_OD = tube_bore + 2*tube_wall
    tube_pocket_OD = tube_OD - 0.5 # for pressfit
    tube_splooge = 0.5  # if the tube was unbotherd, its center point would cause this much overlap with the substrate

    # spring pin spacer parameters
    sp_spacer_encroachment = 2  # amount to encroach on the adapter board non-pin edges
    sp_spacer_encroachment_keepout = 6  # width of central keepout ear/zone

    # width of the top of the resulting countersink (everywhere, generally good for M5)
    csk_diameter = 11

    # radius on the above shelf fillet
    above_shelf_fr = 9

    # radius on the shelf fillet
    shelf_fr = above_shelf_fr

    # adds features on the sides of the shelves to ensure the PCBs get jammed up against their endblocks
    # only really makes sense when extra_x > 0 and x spacing = 0
    use_shelf_PCB_jammers = True

    shelf_height = 5 # thickness of the endblock shelves
    top_mid_height = 4.9+2.2+9.5-pcb_top_bump_up  # estimate

    # constants for the slot-side potting pocket
    potting_pocket_depth = 2
    potting_pocket_fillet = 2

    # potting groove center offset from the inside edges of the walls (for the three non-PCB sides)
    pg_offset = 2.5
    pg_depth = 1  #potting groove depth

    pcb_ph_remain = 2  # number of mm of wall to leave on inner wall of pcb passthrough
    #pcb_phd = wall[2] - 2*pcb_ph_remain  # pcb passthrough potting hole diameter
    pcb_phd = 7  # pcb passthrough potting hole diameter
    pdhd = 1  # potting delivery/vent hole diameter

    chr = tb.c.std_screw_threads['m5']['close_r']  # corner hole radius
    cho = 6  # corner hole offset

    spdhd = 4.25  # spring pin dowel hole depth
    spdd = 2  # spring pin dowel hole diameter
    spd_shift = 3  # shift spring pin dowel holes towards middle this much along y

    sspdhd = 2.5 # side spring pin dowel hole diameter
    sspdh_offset = 2.5  # side spring pin dowel hole offset from edge
    sspdh_depth = 4.25  # side spring pin dowel hole offset from edge

    substrate_thickness = 1.1  # only impacts rendering, not any actual geometry of the setup

    # should the bottom of the pcb slot passthroughs be rounded?
    round_slot_bottom = True  # false is probably impossible to machine (bit becomes too long and thin)

    def __init__(self, array = (4, 1), subs =(30, 30), spacing=(10, 10), padding=(10, 10, 0, 0)):
        self.array = array
        self.substrate_adapters = subs
        self.substrate_spacing = spacing

        # extra room between the device plane and the walls on each side: (-X, +X, -Y, +Y)
        # these must be at least 0.7288 to prevent shadowing when spacing = 0 and shelf_height=5
        #x_minus = pcb_slot_clearance + pcb_thickness/2 # makes sense when spacing = 0
        #x_plus = pcb_slot_clearance + pcb_thickness/2 # makes sense when spacing = 0
        #x_minus = 0
        #x_plus = 0
        x_minus = padding[0]  # was above_shelf_fr
        x_plus = padding[1] # was above_shelf_fr

        # these must be at least 2.5577 to prevent shadowing when yspacing = 0 and shelf_height=5
        y_minus = padding[2] + self.endblock_thickness_extension   # must be at minimum endblock_thickness_extension
        y_plus = padding[3] + self.endblock_thickness_extension  # must be at minimum endblock_thickness_extension
        self.extra = (x_minus, x_plus, y_minus, y_plus)

        self.period = (self.substrate_adapters[0]+self.substrate_spacing[0], self.substrate_adapters[1]+self.substrate_spacing[1])

        logging.basicConfig(format='%(message)s')
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.INFO)

    def replicate(self, thing, cpg):
        """replicates something centered on the points list cps"""
        c = type(self)  # this class
        cps = c.grid2dtolist(*cpg)  # list of points for centers
        return CQ().pushPoints(cps).eachpoint(lambda loc: thing.val().moved(loc), True)
    
    def make_endblock(self):
        """builds one endblock"""
        co = "CenterOfBoundBox"

        block_width = self.substrate_adapters[0]-self.pcb_thickness-2*self.spacer_h
        base = CQ().box(block_width, self.endblock_thickness_shelf, self.wall_height, centered=(True,False,False))
        # drill the mounting hole
        base = base.faces('<Z[-1]').workplane(centerOption=co).hole(tb.c.std_screw_threads['m5']['close_r']*2)
        # make upper PCB mount holes
        base = base.faces('>X[-1]').workplane(centerOption=co).center( self.endblock_thickness_shelf/2-self.pcb_mount_hole_offset, self.wall_height/2-self.pcb_mount_hole_offset).circle(self.eb_mount_hole_tap_r).cutBlind(-self.eb_mount_hole_depth)
        base = base.faces('<X[-1]').workplane(centerOption=co).center(-self.endblock_thickness_shelf/2+self.pcb_mount_hole_offset, self.wall_height/2-self.pcb_mount_hole_offset).circle(self.eb_mount_hole_tap_r).cutBlind(-self.eb_mount_hole_depth)
        # make crossbar pcb side alignment pin holes
        base = base.faces('>X[-1]').workplane(centerOption=co).center(-self.endblock_thickness_shelf/2+self.pcb_mount_hole_offset,-self.wall_height/2+self.pcb_mount_hole_offset).circle(self.pcb_alignment_hole_d/2).cutBlind(-self.pcb_alignment_hole_depth)
        base = base.faces('<X[-1]').workplane(centerOption=co).center( self.endblock_thickness_shelf/2-self.pcb_mount_hole_offset,-self.wall_height/2+self.pcb_mount_hole_offset).circle(self.pcb_alignment_hole_d/2).cutBlind(-self.pcb_alignment_hole_depth)

        extension_a = CQ().box(block_width, self.endblock_thickness_extension, self.pcb_min_height, centered=(True,False,False))
        extension_a = extension_a.translate((0, self.endblock_thickness_shelf, self.pcb_z_float+self.pcb_bottom_bump_down))

        b_width = self.pcb_bottom_bump_offset - self.endblock_thickness_shelf
        b_height =  self.pcb_height-self.pcb_top_bump_up
        extension_b = CQ().box(block_width, b_width, b_height, centered=(True,False,False))
        extension_b = extension_b.translate((0, self.endblock_thickness_shelf, self.pcb_z_float))
        # make lower PCB mount holes
        extension_b = extension_b.faces('>X[-1]').workplane(centerOption=co).center( b_width/2-self.pcb_mount_hole_offset, -b_height/2+self.pcb_mount_hole_offset).circle(self.eb_mount_hole_tap_r).cutBlind(-self.eb_mount_hole_depth)
        extension_b = extension_b.faces('<X[-1]').workplane(centerOption=co).center(-b_width/2+self.pcb_mount_hole_offset, -b_height/2+self.pcb_mount_hole_offset).circle(self.eb_mount_hole_tap_r).cutBlind(-self.eb_mount_hole_depth)

        # combine extensions
        endblock = base.union(extension_a)
        endblock = endblock.union(extension_b)

        # do the counterbore from the bottom for the pusher-downer screw
        endblock = (
            endblock.faces('<Z[-1]').workplane(centerOption=co)  # must be done in to bottom "face" or else not everything gets cut
            .center(0, self.endblock_screw_offset-self.endblock_thickness+self.endblock_thickness_shelf/2)
            .cboreHole(diameter=tb.c.std_screw_threads['m5']['clearance_r']*2, cboreDiameter=tb.c.std_socket_screws['m5']["cbore_r"]*2,cboreDepth=self.pcb_bottom_bump_down+self.pcb_z_float+tb.c.std_socket_screws['m5']["cbore_h"])
            #.cskHole(**tb.c.csk('m5', self.csk_diameter+2*(self.pcb_bottom_bump_down+self.pcb_z_float)))
        )

        # make the top side alignment pin holes
        endblock = endblock.faces('>Z[-2]').workplane(centerOption=co).center(0,self.pcb_cut_rad/2).rarray(self.alignment_pin_spacing,1,2,1).circle(self.pressfit_hole_d/2).cutBlind(-self.pressfit_hole_depth)
        
        # make a lock nut slot in the top extension face
        endblock = endblock.faces('>Z[-2]').workplane(centerOption=co).center(0,self.pcb_cut_rad/2).slot2D(1.5*self.eb_locknut_width, self.eb_locknut_width).cutBlind(-self.eb_locknut_depth)

        # make a lock nut slot in the top base face
        endblock = endblock.faces('>Z[-1]').workplane(centerOption=co).slot2D(1.5*self.eb_locknut_width, self.eb_locknut_width).cutBlind(-self.eb_locknut_depth)

        return endblock
    
    def find_substrate_grid(self):
        """calculates the substrate center grid"""
        c = type(self)  # this class
        return c.mkgrid2d(self.period[0],self.period[1],self.array[0],self.array[1])  # substrate center grid

    def make_endblocks(self, endblock, wp):
        wpf = cq.Face.makeFromWires(wp.val())

        # to get the dims of the working array
        wpbb = wpf.BoundingBox()

        # mirror&duplicate the endblock
        endblockA = CQ().add(endblock.findSolid())
        endblockB = CQ().add(endblock.findSolid()).mirror("ZX")

        # position them properly in y
        endblockA = endblockA.translate((0,-self.endblock_thickness_shelf+wpbb.ymin-self.extra[2],-self.wall_height+self.pcb_top_bump_up))
        endblockB = endblockB.translate((0, self.endblock_thickness_shelf+wpbb.ymax+self.extra[3],-self.wall_height+self.pcb_top_bump_up))
        endblocks = CQ().add(endblockA).add(endblockB).combine(glue=True)

        # replicate them along X:
        endblock_array = (
            CQ().rarray(xSpacing=(self.period[0]), ySpacing=1, xCount=self.array[0], yCount=1)
            .eachpoint(lambda loc: endblocks.val().moved(loc), True)
        )

        return endblock_array

    def make_adapter(self):
        """makes one substrate adapter"""
        adapter = CQ().rect(*self.substrate_adapters).extrude(self.pcb_thickness)

        window = CQ().rect(self.substrate_adapters[0]-2*self.sa_border_thickness[0], self.substrate_adapters[1]-2*self.sa_border_thickness[1])
        window_void = window.extrude(self.pcb_thickness).edges('|Z').fillet(self.pcb_cut_rad)

        # make window cuts
        adapter = adapter.cut(window_void)

        # places for the spring pins
        pin_points =              CQ().center(0, 2*2*2.54).rarray(self.substrate_adapters[0]-self.sa_spring_hole_offset*2, 2.5, 2, 2).vals()
        pin_points = pin_points + CQ().center(0, 1*2*2.54).rarray(self.substrate_adapters[0]-self.sa_spring_hole_offset*2, 2.5, 2, 2).vals()
        pin_points = pin_points + CQ().center(0, 0*2*2.54).rarray(self.substrate_adapters[0]-self.sa_spring_hole_offset*2, 2.5, 2, 2).vals()
        pin_points = pin_points + CQ().center(0,-1*2*2.54).rarray(self.substrate_adapters[0]-self.sa_spring_hole_offset*2, 2.5, 2, 2).vals()
        pin_points = pin_points + CQ().center(0,-2*2*2.54).rarray(self.substrate_adapters[0]-self.sa_spring_hole_offset*2, 2.5, 2, 2).vals()

        # fillet corners
        #adapter = adapter.edges('|Z').fillet(self.pcb_cut_rad)

        # locations for the edge socket holes
        sh_points = CQ().rarray(self.substrate_adapters[0]-2, 2, 2, 12).vals() + CQ().rarray(self.substrate_adapters[0]+2, 2, 2, 12).vals()

        # make single example cylinders to replicate
        small_cylinder = CQ().circle(self.sa_socket_hole_d/2).extrude(self.pcb_thickness)
        less_small_cylinder =  CQ().circle(self.sa_spring_hole_d/2).extrude(self.pcb_thickness)

        # make the hole volumes
        small_holes = CQ().pushPoints(sh_points).eachpoint(lambda l: small_cylinder.val().located(l))
        less_small_holes = CQ().pushPoints(pin_points).eachpoint(lambda l: less_small_cylinder.val().located(l))

        # cut out the hole volumes
        adapter = adapter.cut(small_holes).cut(less_small_holes)

        return adapter


    def mkgrid2d(x_period, y_period, nx, ny):
        """makes an x-y 2d grid given x and y periods and number of items for each"""
        x_grid, y_grid = np.mgrid[0:nx, 0:ny]
        x_vals = x_grid*x_period-(nx-1)*x_period/2
        y_vals = y_grid*y_period-(ny-1)*y_period/2
        return x_vals, y_vals
    
    def grid2dtolist(x_grid, y_grid):
        """converts 2d grid to list of points"""
        return [(float(p[0]), float(p[1])) for p in zip(x_grid.flatten(), y_grid.flatten())]
    
    def make_sandwich_wires(self, wp, alignment_pin_hole_d, aux_con_hole_d, aux_con_pad_hole_d):
        """makes the wires for the basic sandwich outline shape"""
        co = "CenterOfBoundBox"
        c = type(self)  # this class

        # werkplane face
        wpf = cq.Face.makeFromWires(wp.val())

        # to get the dims of the working array
        wpbb = wpf.BoundingBox()

        one = 1  # extrude everything here to 1mm just so we can operate in 3D (output is wires)
        # make the board bulk
        sand = CQ().add(wp).toPending().extrude(one)
        sand = sand.faces("<Y[-1]").wires().toPending().workplane().extrude(self.extra[2] - self.pcb_cut_rad)
        sand = sand.faces(">Y[-1]").wires().toPending().workplane().extrude(self.extra[3] - self.pcb_cut_rad)
        sand = sand.faces("<X[-1]").wires().toPending().workplane().extrude(self.extra[0]-self.sandwich_xbuffer)  # come in from xwall
        sand = sand.faces(">X[-1]").wires().toPending().workplane().extrude(self.extra[1]-self.sandwich_xbuffer)  # come in from xwall

        # center of the shelf on the plus and minus y sides
        shelf_y_minus_center = wpbb.ymin - self.extra[2] + self.endblock_thickness_extension - self.endblock_screw_offset
        shelf_y_plus_center  = wpbb.ymax + self.extra[3] - self.endblock_thickness_extension + self.endblock_screw_offset

        # make clamping screw holes
        shg = c.mkgrid2d(self.period[0], 1, self.array[0], 1)  # screw hole point grid
        shp = c.grid2dtolist(shg[0], shg[1]+shelf_y_minus_center) + c.grid2dtolist(shg[0], shg[1]+shelf_y_plus_center)  # list of points for clamp screw holes
        shv = CQ().circle(tb.c.std_screw_threads['m5']['clearance_r']).extrude(1)  # volume for a single clamp screw hole
        shvs = CQ().pushPoints(shp).eachpoint(lambda l: shv.val().located(l))  # volumes for all the clamp screw holes
        sand = sand.cut(shvs)  # drill the clamp screw holes

        # make alignment pin holes
        ahpag = shg[0]-self.alignment_pin_spacing/2  # alignment pin a x position grid
        ahpbg = shg[0]+self.alignment_pin_spacing/2  # alignment pin b x position grid
        ahp = (  # list of alignment pin locations
            c.grid2dtolist(ahpag, shg[1] + shelf_y_minus_center) + 
            c.grid2dtolist(ahpbg, shg[1] + shelf_y_minus_center) + 
            c.grid2dtolist(ahpag, shg[1] + shelf_y_plus_center) + 
            c.grid2dtolist(ahpbg, shg[1] + shelf_y_plus_center)
        )
        ahv = CQ().circle(alignment_pin_hole_d/2).extrude(one)  # volume for a single alignment pin hole
        ahvs = CQ().pushPoints(ahp).eachpoint(lambda l: ahv.val().located(l))  # volumes for all the alignment pin holes
        sand = sand.cut(ahvs)  # drill the alignment pin holes

        # make aux electrical connection pin receptical holes in the substrate spacer layer
        # and also put holes assocated with connection pad locations for these
        row_centerg = c.mkgrid2d(self.period[0],1,self.array[0],1)  # grid of row centers
        row_centerp = c.grid2dtolist(*row_centerg)   # list of row center points
        aehg = c.mkgrid2d(self.substrate_adapters[0]-2, 2, 2, 6)  # aux electrical connection point grid
        aepg = c.mkgrid2d(self.substrate_adapters[0]-2-4, 2, 2, 6)  # aux electrical pad point grid
        aecy1 = aehg[1] + shelf_y_minus_center  # y vales for the connection points & pads
        aecy2 = aehg[1] + shelf_y_plus_center  # y vales for the connection points & pads
        # do array of array to build up a list of the points for all the aux electrical hole and pad locations
        aehp = []
        aepp = []
        for row_center in row_centerp:
            aehp = aehp + c.grid2dtolist(aehg[0]+row_center[0], aecy1) + c.grid2dtolist(aehg[0]+row_center[0], aecy2)  # for connection points from crossbars
            aepp = aepp + c.grid2dtolist(aepg[0]+row_center[0], aecy1) + c.grid2dtolist(aepg[0]+row_center[0], aecy2)  # for associated pad points
        aehv = CQ().circle(aux_con_hole_d/2).extrude(one)  # for connection points from crossbars
        aepv = CQ().circle(aux_con_pad_hole_d/2).extrude(one)  # for associated pad points
        aehvs = CQ().pushPoints(aehp).eachpoint(lambda l: aehv.val().located(l))
        aepvs = CQ().pushPoints(aepp).eachpoint(lambda l: aepv.val().located(l))
        sand = sand.cut(aehvs).cut(aepvs)  # drill the aux connection holes and holes associated with pad locations

        return sand.faces("<Z[-1]").wires()

    def make_adapter_spacer(self, wp, cpg):
        """makes the substrate adapter spacer PCB"""
        co = "CenterOfBoundBox"
        c = type(self)  # this class

        # make adapter spacer basic shape
        adp_spc = CQ().add(self.make_sandwich_wires(wp, self.alignment_pin_clear_d, self.sa_socket_hole_d, self.aux_con_pad_hole_d)).toPending().extrude(self.pcb_thickness)

        # make pcb window(s)
        wv = (  # volume for a single window
            CQ().rect(self.substrate_adapters[0]+self.pcb_cut_rad, self.substrate_adapters[1]+self.pcb_cut_rad)
            .extrude(self.pcb_thickness)
        )
        cps = c.grid2dtolist(*cpg)  # list of points for centers
        wvs = CQ().pushPoints(cps).eachpoint(lambda l: wv.val().located(l))  # volumes for all the windows
        adp_spc = adp_spc.cut(wvs)  # cut out the windows
        adp_spc = adp_spc.edges('|Z').fillet(self.pcb_cut_rad)  # round all the board edges

        return adp_spc

    def make_some_layers(self, wp, cpg):
        """builds a few of the tightly coupled sandwich layers"""
        c = type(self)  # this class
        s = self

        # werkplane face
        wpf = cq.Face.makeFromWires(wp.val())

        # to get the dims of the working array
        wpbb = wpf.BoundingBox()

        if (self.substrate_spacing[0] >= 10) and (self.substrate_spacing[1] >= 10):
            many_pockets = True  # we have enough room to do pockets for every substrate
        else:
            many_pockets = False
        
        if (self.substrate_spacing[0] == 0) and (self.substrate_spacing[1] == 0):
            unipocket = True  # treat all the substrates as a unit, making one big holder pocket
        else:
            unipocket = False

        # spring pin spacer base
        sp_spc = CQ().add(self.make_sandwich_wires(wp,self.alignment_pin_clear_d, self.sa_socket_hole_d, self.aux_con_pin_clearance_d)).toPending().extrude(self.sa_spacing)
        sp_spc = sp_spc.edges('|Z').fillet(self.pcb_cut_rad)  # round the outside edges

        # make spring pin spacer layer windows
        spswv = (  # volume for a single window
            CQ().rect(self.substrate_adapters[0]+self.pcb_cut_rad, self.substrate_adapters[1]-2*self.sp_spacer_encroachment)
            .extrude(self.sa_spacing)
        )
        spswv = spswv.cut(
            CQ().rect(self.substrate_adapters[0]-2*self.sa_border_thickness[0], self.substrate_adapters[1]+self.pcb_cut_rad)
            .extrude(self.sa_spacing)
        )
        # come way in on the y edges
        spswv = spswv.edges('|Z').fillet(self.pcb_cut_rad)  # round the window edges
        spswv = spswv.union(
            CQ().rect(self.substrate_adapters[0], self.substrate_adapters[1]-2*self.sa_border_thickness[1])
            .extrude(self.sa_spacing)
        )
        # but leave ears for the smt parts on the adapters (TODO: this creates impossible geometry for zero spacing case)
        spswv = spswv.edges('|Z').fillet(self.pcb_cut_rad)  # round the window edges
        spswv = spswv.union(
            CQ().rect(self.sp_spacer_encroachment_keepout, self.substrate_adapters[1])
            .extrude(self.sa_spacing)
            .edges('|Z').fillet(self.pcb_cut_rad)
        )

        cps = c.grid2dtolist(*cpg)  # list of points for centers
        spswvs = CQ().pushPoints(cps).eachpoint(lambda l: spswv.val().located(l))
        sp_spc = sp_spc.cut(spswvs)  # cut out the windows

        # generate the sample holder base
        sh = CQ().add(self.make_sandwich_wires(wp,self.alignment_pin_slide_d, self.sa_socket_hole_d, self.aux_con_pin_clearance_d)).toPending().extrude(self.sa_spacing)

        apps = []  # no alignment pin points by default
        tps = []  # no tube points by default
        if many_pockets == True:
            # calculate substrate alignment pin grids
            gx1 = cpg[0]-s.substrate_adapters[0]/2-s.sapd/2
            gx2 = cpg[0]-s.substrate_adapters[0]/2-s.sapd/2
            gx3 = cpg[0]-s.substrate_adapters[0]*s.sap_offset_fraction
            gx4 = cpg[0]+s.substrate_adapters[0]*s.sap_offset_fraction

            gy1 = cpg[1]+s.substrate_adapters[1]*s.sap_offset_fraction
            gy2 = cpg[1]-s.substrate_adapters[1]*s.sap_offset_fraction
            gy3 = cpg[1]-s.substrate_adapters[1]/2-s.sapd/2
            gy4 = cpg[1]-s.substrate_adapters[1]/2-s.sapd/2

            # generate substrate alignment pin points list
            apps = (
                c.grid2dtolist(gx1,gy1) +
                c.grid2dtolist(gx2,gy2) +
                c.grid2dtolist(gx3,gy3) +
                c.grid2dtolist(gx4,gy4)
            )

            # calculate squishy tube centers
            tgx1 = cpg[0]
            tgx2 = cpg[0] + s.substrate_adapters[0]/2 + s.tube_OD/2 - s.tube_splooge
            tgy1 = cpg[1] + s.substrate_adapters[1]/2 + s.tube_OD/2 - s.tube_splooge
            tgy2 = cpg[1]

            # generate the tube hole center points list
            tps = (
                c.grid2dtolist(tgx1,tgy1) +
                c.grid2dtolist(tgx2,tgy2)
            )
        elif unipocket == True:
            # calculate substrate alignment pin locations
            x1 =  wpbb.xmin-s.sapd/2
            x2 =  wpbb.xmin-s.sapd/2
            x3 = -wpbb.xlen*s.sap_offset_fraction
            x4 =  wpbb.xlen*s.sap_offset_fraction

            y1 =  wpbb.ylen*s.sap_offset_fraction
            y2 = -wpbb.ylen*s.sap_offset_fraction
            y3 =  wpbb.ymin-s.sapd/2
            y4 =  wpbb.ymin-s.sapd/2

            # generate substrate alignment pin points list
            apps = [
                (x1, y1),
                (x2, y2),
                (x3, y3),
                (x4, y4),
            ]

            # calculate squishy tube centers
            tx1 = 0
            tx2 = wpbb.xmax + s.tube_OD/2 - s.tube_splooge
            ty1 = wpbb.ymax + s.tube_OD/2 - s.tube_splooge
            ty2 = 0

            # generate the tube hole center points list
            tps = [
                (tx1,ty1),
                (tx2,ty2),
            ]

        # make one substrate alignment pin hole volume for the spring pin spacer layer
        aphv = CQ().circle(s.sapd/2).extrude(self.sa_spacing)
        aphvs = CQ().pushPoints(apps).eachpoint(lambda l: aphv.val().located(l))  # replicate that

        # cut out substrate alignment pin hole volumes
        sp_spc = sp_spc.cut(aphvs)

        # make one tube clearance hole volume for the spring pin spacer layer
        thv = CQ().circle(s.tube_OD/2).extrude(self.sa_spacing)
        thvs = CQ().pushPoints(tps).eachpoint(lambda l: thv.val().located(l))  # replicate that

        # cut out substrate alignment pin hole volumes
        sp_spc = sp_spc.cut(aphvs)

        # cut out the tube hole volumes
        sp_spc = sp_spc.cut(thvs)

        return sp_spc

    # the purpose of this is to generate a crossbar outline shape guaranteed to match the chamber geometry for import into pcbnew
    def make_crossbar(self, wp):
        """makes a crossbar PCBs"""
        # werkplane face
        wpf = cq.Face.makeFromWires(wp.val())

        # to get the dims of the working array
        wpbb = wpf.BoundingBox()

        crossbar_points = [  # board outline points
            (wpbb.ymax + self.extra[3], 0),
            (wpbb.ymax + self.extra[3], self.pcb_top_bump_up),
            (wpbb.ymax + self.extra[3] + self.endblock_thickness_shelf,  self.pcb_top_bump_up),
            (wpbb.ymax + self.extra[3] + self.endblock_thickness_shelf, -self.pcb_min_height - self.pcb_bottom_bump_down),
            (wpbb.ymax + self.extra[3] + self.endblock_thickness_shelf - self.pcb_bottom_bump_offset, -self.pcb_min_height - self.pcb_bottom_bump_down),
            (wpbb.ymax + self.extra[3] + self.endblock_thickness_shelf - self.pcb_bottom_bump_offset, -self.pcb_min_height),
            (wpbb.ymin - self.extra[2] - self.endblock_thickness_shelf + self.pcb_bottom_bump_offset, -self.pcb_min_height),
            (wpbb.ymin - self.extra[2] - self.endblock_thickness_shelf + self.pcb_bottom_bump_offset, -self.pcb_min_height - self.pcb_bottom_bump_down),
            (wpbb.ymin - self.extra[2] - self.endblock_thickness_shelf, -self.pcb_min_height - self.pcb_bottom_bump_down),
            (wpbb.ymin - self.extra[2] - self.endblock_thickness_shelf,  self.pcb_top_bump_up),
            (wpbb.ymin - self.extra[2], self.pcb_top_bump_up),
            (wpbb.ymin - self.extra[2], 0),
        ]

        crossbar_mount_hole_points = [  # locate pcb mounting holes
            (wpbb.ymax + self.extra[3] + self.pcb_mount_hole_offset, self.pcb_top_bump_up - self.pcb_mount_hole_offset),
            (wpbb.ymax + self.extra[3] + self.endblock_thickness_shelf - self.pcb_bottom_bump_offset + self.pcb_mount_hole_offset, -self.pcb_min_height - self.pcb_bottom_bump_down + self.pcb_mount_hole_offset),
            (wpbb.ymin - self.extra[2] - self.pcb_mount_hole_offset, self.pcb_top_bump_up - self.pcb_mount_hole_offset),
            (wpbb.ymin - self.extra[2] - self.endblock_thickness_shelf + self.pcb_bottom_bump_offset - self.pcb_mount_hole_offset, -self.pcb_min_height - self.pcb_bottom_bump_down + self.pcb_mount_hole_offset),
        ]

        alignment_hole_point = [
            (wpbb.ymax + self.extra[3] + self.endblock_thickness_shelf - self.pcb_mount_hole_offset, crossbar_mount_hole_points[1][1]),
            (wpbb.ymin - self.extra[2] - self.endblock_thickness_shelf + self.pcb_mount_hole_offset, crossbar_mount_hole_points[3][1]),
        ]

        # make the part
        innter_crossbar = CQ('YZ').polyline(crossbar_points).close().extrude(self.pcb_thickness)

        # drill the endblock mounting holes
        innter_crossbar = innter_crossbar.pushPoints(crossbar_mount_hole_points).circle(self.pcb_mount_hole_d/2).cutThruAll()
        innter_crossbar = innter_crossbar.pushPoints(alignment_hole_point).circle(self.pcb_alignment_hole_d/2).cutThruAll()

        # calculate the extra board length required to ensure the inch connectors are on-grid
        wall_end = wpbb.ymax + self.extra[2] + self.endblock_thickness_shelf + self.endblock_wall_spacing + self.wall[2]
        self.pcb_inch_fudge = round(math.ceil(wall_end/1.27)*1.27-wall_end, 2)  # so that the inch-based connectors can be on-grid

        extension_length = self.endblock_wall_spacing+self.wall[2]+self.pcb_inch_fudge+self.pcb_external_connector_width*self.array[1]
        
        # extra extension length needed to get the board outline on 0.25 mm grid
        self.pcb_extension_fidge = round(math.ceil(extension_length/0.25)*0.25-extension_length,2)

        # fudge extension length to get it on mm grid
        extension_length = round(extension_length + self.pcb_extension_fidge, 2)

        # extend for external connectors
        crossbar = (
            CQ(innter_crossbar.findSolid())
            .faces("<Y[-1]").wires().toPending().workplane().extrude(extension_length)
        )

        # fillet the edges fails now because of one place
        #crossbar = crossbar.edges('|X').fillet(self.pcb_cut_rad)

        return(crossbar.translate((-self.pcb_thickness/2, 0, 0)))

    def make_crossbars(self, crossbar):
        # replicate the crossbars:
        crossbars = (
            CQ().rarray(xSpacing=(self.period[0]), ySpacing=1, xCount=self.array[0], yCount=1)
            .eachpoint(lambda loc: crossbar.val().moved(loc), True)
        )

        crossbars_a = crossbars.translate([-self.substrate_adapters[0]/2,0,0])
        crossbars_b = crossbars.translate([ self.substrate_adapters[0]/2,0,0])

        crossbar_array = CQ().add(crossbars_a).add(crossbars_b)

        return crossbar_array

    def make_plane(self):
        """makes a reference workplane situated on top of the crossbars covering
        spacing plus adapters (always a centered rectangle)"""
        s = self
        planex = s.array[0]*(s.substrate_adapters[0]+s.substrate_spacing[0])
        planey = s.array[1]*(s.substrate_adapters[1]+s.substrate_spacing[1])
        werkplane = CQ().rect(planex, planey)
        return werkplane

    def make_middle(self, wp):
        s = self
        co = "CenterOfBoundBox"
        c = type(self)  # my class

        # slot bottom round radius
        if s.round_slot_bottom == True:
            bsrr = (s.pcb_thickness+2*s.pcb_slot_clearance)/2
        else:
            bsrr = 0
        s.wall_height = s.pcb_height + s.pcb_z_float # if we don't round the bottom, leave some z float for the pcb
        
        if (s.substrate_spacing[0]/2 + s.extra[0]) <  (2*self.pcb_slot_clearance + self.pcb_thickness)/2:
            s.log.warning('Slots will be cut into the inner -X wall')
        
        if (s.substrate_spacing[0]/2 + s.extra[1]) <  (2*self.pcb_slot_clearance + self.pcb_thickness)/2:
            s.log.warning('Slots will be cut into the inner +X wall')

        shelf_width = s.endblock_wall_spacing + s.endblock_thickness_shelf

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

        # non-slot side shelf endblock mounting block holes
        shelved_ring = (
            shelved_ring.faces('+Z').faces('>Y').workplane(centerOption=co, invert=True, offset=s.shelf_height)
            .center((s.extra[0]-s.extra[1])/2, +shelf_width/2-s.endblock_thickness_shelf/2)  # invert=True flips Y but not X
            .rarray(xSpacing=(s.period[0]), ySpacing=1, xCount=s.array[0], yCount=1)
            .cskHole(**tb.c.csk('m5', s.csk_diameter))
        )

        # slot side shelf endblock mounting block holes
        shelved_ring = (
            shelved_ring.faces('+Z').faces('<Y').workplane(centerOption=co, invert=True, offset=s.shelf_height)
            .center((s.extra[0]-s.extra[1])/2, -shelf_width/2+s.endblock_thickness_shelf/2)  # invert=True flips Y but not X
            .rarray(xSpacing=(s.period[0]), ySpacing=1, xCount=s.array[0], yCount=1)
            .cskHole(**tb.c.csk('m5', s.csk_diameter))
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
        srbb = shelved_ring.findSolid().BoundingBox()

        # use an offset to find the path for the potting slot
        pot_slot_path = CQ(shelved_ring.faces(">Z[-1]").wires().vals()[0].offset2D(s.pg_offset)[0])

        # cut the corner holes
        chp = [  # corner hole points
        (srbb.xmin+s.cho, srbb.ymin+s.cho),
        (srbb.xmax-s.cho, srbb.ymin+s.cho),
        (srbb.xmin+s.cho, srbb.ymax-s.cho),
        (srbb.xmax-s.cho, srbb.ymax-s.cho),
        ]
        shelved_ring = shelved_ring.faces(">Z[-1]").workplane().pushPoints(chp).hole(s.chr*2)

        # form PCB slot cutters
        c_len = wpbb.ylen + 2*s.endblock_thickness_shelf + s.extra[2] + s.extra[3] + s.wall[2] + s.endblock_wall_spacing  # length of the slot cutter
        
        holes_y_spot = srbb.ymin+s.wall[2]-s.pcb_ph_remain-s.pcb_phd/2
        _pcb_slot_void = (
            CQ()
            .workplane(offset=-s.pcb_height)
            .box(s.pcb_thickness+2*s.pcb_slot_clearance, c_len, s.pcb_height, centered=[True, False, False])
        )

        if s.round_slot_bottom == True:
            # bottom round the PCB slots
            _pcb_slot_void = (
                CQ(_pcb_slot_void.findSolid())
                .faces("<Y[-1]").workplane(centerOption=co)
                .move(0, -s.pcb_height/2).circle(bsrr).extrude(-s.wall[2])
            )
        else:  # no rounded bottom, so extend the slot to cover pcb z float
            _pcb_slot_void = (
                CQ(_pcb_slot_void.findSolid())
                .faces("<Z[-1]").wires().toPending().workplane().extrude(s.pcb_z_float)
            )

        # so that the slots are cut in the -Y wall
        _pcb_slot_void = _pcb_slot_void.translate([0, -c_len+wpbb.ymax+s.extra[3]+s.endblock_thickness_shelf, 0])

        # add the pcb passthrough potting holes
        _pcb_slot_void = (
            CQ(_pcb_slot_void.findSolid())
            .faces(">Z[-1]").workplane()
            .move(0, holes_y_spot).circle(s.pcb_phd/2).extrude(-s.wall_height)
        )

        # drill the fill/vent holes
        _pcb_slot_void = (
            CQ(_pcb_slot_void.findSolid())
            .faces(">Z[-1]").workplane()
            .move(0, holes_y_spot).circle(s.pdhd/2).extrude(-srbb.zlen)
        )

        # replicate the pcb slot cutter shapes:
        _pcb_slot_void = (
            CQ().rarray(xSpacing=(s.period[0]), ySpacing=1, xCount=s.array[0], yCount=1)
            .eachpoint(lambda loc: _pcb_slot_void.val().moved(loc), True)
        )

        # cut the PCB slots
        shelved_ring = shelved_ring.cut(_pcb_slot_void.translate([-s.substrate_adapters[0]/2,0,0]))
        shelved_ring = shelved_ring.cut(_pcb_slot_void.translate([ s.substrate_adapters[0]/2,0,0]))

        # the side potting pocket
        #side_pot_cutter = (
        #    CQ()
        #    .box(wpbb.xlen+2*s.potting_pocket_fillet+s.pcb_thickness+2*s.pcb_slot_clearance, 4*s.potting_pocket_depth, s.wall_height+2*s.potting_pocket_fillet, centered=[True, False, False])
        #    .translate([0, -4*s.potting_pocket_depth+wpbb.ymin-s.extra[2]-shelf_width-s.wall[2]+s.potting_pocket_depth, -s.wall_height-s.potting_pocket_fillet])
        #    #.edges().fillet(s.potting_pocket_fillet)
        #    #.edges().chamfer(s.potting_pocket_fillet)
        #)
        #shelved_ring = shelved_ring.cut(side_pot_cutter)

        # now cut the vgroove bevels in the side potting pocket
        #spcbb = side_pot_cutter.findSolid().BoundingBox()
        #svg = tb.groovy.mk_vgroove(CQ().rect(spcbb.xlen, spcbb.zlen, centered=False), (0,spcbb.zlen/2,0), s.potting_pocket_depth)
        #svg = svg.translate((-spcbb.xlen/2, -spcbb.zlen, 0))
        #svg = svg.rotate((0,0,0), (1,0,0), 90)
        #svg = svg.translate((0,srbb.ymin,s.potting_pocket_fillet))
        #shelved_ring = shelved_ring.cut(svg)

        ## now cut the paths to the entry/exit
        #cone = cq.Solid.makeCone(0,s.potting_pocket_depth, s.potting_pocket_depth, dir=cq.Vector(0,-1,0))
        #cone_right = CQ('XZ').add(cone).translate((srbb.xmax-s.pg_offset,srbb.ymin+s.potting_pocket_depth,0)) # srbb.ymin-s.potting_pocket_depth
        #cone_left = cone_right.mirror(mirrorPlane='YZ')
        #shelved_ring = shelved_ring.cut(cone_right)
        #shelved_ring = shelved_ring.cut(cone_left)
        #btw_path = CQ("YZ").polyline([(0,0),(-s.potting_pocket_depth,-s.potting_pocket_depth),(-s.potting_pocket_depth,s.potting_pocket_depth)]).close().extrude(srbb.xlen-2*s.pg_offset).translate((srbb.xmin+s.pg_offset,srbb.ymin+s.potting_pocket_depth,0))
        #shelved_ring = shelved_ring.cut(btw_path)

        # add spring pin dowel holes in the top corners
        dowel_points = [
            (srbb.xmin + s.wall[0] - s.pg_offset, srbb.ymax - s.spd_shift - s.wall[3] + s.pg_offset),
            (srbb.xmax - s.wall[1] + s.pg_offset, srbb.ymax - s.spd_shift - s.wall[3] + s.pg_offset),
            (srbb.xmax - s.wall[1] + s.pg_offset, srbb.ymin + s.spd_shift + s.wall[2] - s.pg_offset),
            (srbb.xmin + s.wall[0] - s.pg_offset, srbb.ymin + s.spd_shift + s.wall[2] - s.pg_offset),
        ]

        # caculate spring pin hole centers in - and + y walls
        dp_centers = c.mkgrid2d(self.period[0],1,self.array[0],1)
        dp_centers_a = dp_centers[1]+srbb.ymin + s.wall[2]/2
        dp_centers_b = dp_centers[1]+srbb.ymax - s.wall[3]/2
        y_wall_dp_centers = c.grid2dtolist(dp_centers[0],dp_centers_a)+c.grid2dtolist(dp_centers[0],dp_centers_b)

        dowel_points = dowel_points+y_wall_dp_centers

        #shp = c.grid2dtolist(*shg)  # list of points for clamp screw holes
        #shv = CQ().circle(tb.c.std_screw_threads['m5']['clearance_r']).extrude(self.pcb_thickness)  # volume for a single clamp screw hole
        #shvs = CQ().pushPoints(shp).eachpoint(lambda l: shv.val().located(l))  # volumes for all the clamp screw holes
        #adp_spc = adp_spc.cut(shvs)  # drill the clamp screw holes

        # make alignment pin holes
        #ahpag = shg[0]-self.alignment_pin_spacing/2  # alignment pin a x position grid
        #ahpbg = shg[0]+self.alignment_pin_spacing/2  # alignment pin b x position grid

        #for i in range(self.array):
        #    dowel_points.append()


        dowel_voids = CQ().pushPoints(dowel_points).circle(s.spdd/2).extrude(s.spdhd, both=True)
        shelved_ring = shelved_ring.cut(dowel_voids)

        # add spring pin dowel holes in the pcb side
        #shelved_ring = (
        #    CQ(shelved_ring.findSolid())
        #    .faces('<Y[-1]').workplane(centerOption=co)
        #    .pushPoints([(srbb.xmax-s.sspdh_offset, 0), (srbb.xmin+s.sspdh_offset, 0)])
        #    .circle(s.sspdhd/2).cutBlind(-s.sspdh_depth)
        #)

        # split the two pieces
        top = shelved_ring.faces('>Z[-1]').workplane(-s.top_mid_height).split(keepTop=True)
        middle = shelved_ring.faces('>Z[-1]').workplane(-s.top_mid_height).split(keepBottom=True)

        # cut the v potting groove for the potting between the pieces
        pg = tb.groovy.mk_vgroove(pot_slot_path, (srbb.xmin + s.wall[0] - s.pg_offset, 0, 0), s.pg_depth)
        middle = middle.cut(pg)

        return (middle, top.clean())  # clean() to remove unwanted lines in faces

    def build(self):
        s = self
        asy = cadquery.Assembly()

        # the device plane
        werkplane = self.make_plane()
        asy.add(werkplane, name="werkplane")
        
        # make the middle pieces
        middle, top_mid= self.make_middle(werkplane)
        asy.add(middle.translate((0,0,self.woff)), name="middle", color=cadquery.Color("orange"))
        asy.add(top_mid.translate((0,0,self.woff)), name="top_mid", color=cadquery.Color("yellow"))

        # generate a crossbar PCB core (needed for outline export) 
        crossbar = self.make_crossbar(werkplane)

        # replicate the crossbar
        crossbars = self.make_crossbars(crossbar)
        asy.add(crossbars, name="crossbars", color=cadquery.Color("darkgreen"))

        endblock = self.make_endblock()
        endblocks = self.make_endblocks(endblock, werkplane)
        asy.add(endblocks, name="endblocks", color=cadquery.Color("gray"))

        # generate the substrate center grid
        cpg = self.find_substrate_grid()

        substrate = CQ().rect(*self.substrate_adapters).extrude(self.substrate_thickness)
        substrates = self.replicate(substrate, cpg).translate((0, 0, self.pcb_thickness+self.sa_spacing))
        #asy.add(substrates.translate((0,0,4)), name="substrates", color=cadquery.Color("lightblue"), alpha=0.4)
        # shoould be "lightblue" with alpha = 0.3 but alpha is broken?
        asy.add(substrates, name="substrates", color=cadquery.Color(107/255,175/255,202/255,0.3))

        adapter = self.make_adapter()
        adapters = self.replicate(adapter, cpg)
        asy.add(adapters, name="adapters", color=cadquery.Color("darkgreen"))

        adapter_spacer = self.make_adapter_spacer(werkplane, cpg)
        asy.add(adapter_spacer, name="adapter_spacer", color=cadquery.Color("darkgreen"))

        spring_pin_spacer = self.make_some_layers(werkplane, cpg)
        asy.add(spring_pin_spacer.translate((0,0,self.pcb_thickness)), name="spring_pin_spacer", color=cadquery.Color("black"))

        return (asy, crossbar, adapter, adapter_spacer, spring_pin_spacer)

def main():
    s = ChamberNG(array=(1, 1), subs =(30, 30), spacing=(10, 10), padding=(5,5,0,0))
    #s = ChamberNG(array=(1, 4), subs =(30, 30), spacing=(10, 10), padding=(5,5,0,0))
    #s = ChamberNG(array=(5, 5), subs =(30, 30), spacing=(0, 0), padding=(10,10,5,5))
    (asy, crossbar, adapter, adapter_spacer, spring_pin_spacer) = s.build()
    
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
                cadquery.exporters.export(c.locate(val.loc), f'{val.name}.stl')
        
        # save DXFs
        crossbar_outline = CQ().add(crossbar.rotate((0,0,0),(0,1,0),-90).rotate((0,0,0),(0,0,1),-90)).section()
        cadquery.exporters.exportDXF(crossbar_outline, 'crossbar_outline.dxf')

        adapter_outline = adapter.section()
        cadquery.exporters.exportDXF(adapter_outline, 'adapter_outline.dxf')

        adapter_spacer_outline = CQ().add(adapter_spacer.findSolid()).section()  # add to new wp to fix orientation
        cadquery.exporters.exportDXF(adapter_spacer_outline, 'adapter_spacer_outline.dxf')

        spring_pin_spacer_outline = spring_pin_spacer.section()
        cadquery.exporters.exportDXF(spring_pin_spacer_outline, 'spring_pin_spacer_outline.dxf')

main()