#!/usr/bin/env python3
import cadquery
from cadquery import CQ, cq
import geometrics.toolbox as tb
import logging
import math
import numpy as np

import serial
s = serial.Serial()


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

    # gas feedthroughs from the sides
    do_gas_feedthroughs = False
    feedthrough_d = 10

    # subadapter pcb paramters
    #sa_pcb_thickness = 1
    #sa_pcb_border_thickness = (1.75, 1.75)  # (pin side, non-pin side)
    #sa_pf_hole_d = 0.5  # for pressfit pins (shaft nominal d = 0.457mm
    
    # substrate adapter parameters
    sa_spring_hole_d = 1.78  # spring pin mount hole diameter (pn 0921-1)
    sa_spring_hole_offset = 3.25  # from edge of board
    sa_socket_hole_d = 1.35  # pin socket mounting hole diameter (pn 5342)
    sa_border_thickness = (5.1, 3)  # defines the window border width (pin side, non-pin side)

    # aux connection parameters
    aux_pads_n = 6  # number of pads/connections in row
    aux_pad_center_shift = 0  # shift the pads to center of array by this much

    # adapter spacer parameters
    as_aux_pad_hole_d = 0  # for the holes that correspond to where the aux pads would be
    as_aux_pin_clearance_d = 1.0  # for the holes above the connector pins

    # workplane offset from top of PCB
    woff = pcb_top_bump_up

    # (normal plane) clearance given around the crossbar PCBs when cutting their slots in the wall
    pcb_slot_clearance = pcb_thickness*0.10  # covers a PCB that's 10 percent too thick
    pcb_z_float = 0.25  # floats the PCB bottom off the shelf by this much

    endblock_wall_spacing = 0.5  # from + and - Y walls
    endblock_thickness_shelf = 12
    endblock_thickness_extension = 12 + pcb_cut_rad
    endblock_screw_offset = 6  # distance from the endblock edge to clamp screw hole center
    endblock_thickness = endblock_thickness_shelf + endblock_thickness_extension
    eb_locknut_depth = 5
    eb_locknut_width = tb.c.std_hex_nuts["m5"]["flat_w"]
    eb_mount_hole_depth = 4  # threaded mount hole depth
    eb_mount_hole_tap_r = tb.c.std_screw_threads['m2']["tap_r"]  # for accu screw pn SSB-M2-6-A2
    pressfit_hole_d_nominal = 3  # alignment pin nominal dimension
    pressfit_hole_d = pressfit_hole_d_nominal - 0.035  # used in sizing the holes for endblock pressfits
    alignment_pin_clear_d = pressfit_hole_d_nominal + 0.45  # used in sizing holes in sandwich layers
    alignment_pin_slide_d = pressfit_hole_d_nominal + 0.15  # for the holes in the substrate holder layer
    spacer_h = 2.0  # for accu pn HPS-5-2-BR-NI
    alignment_pin_spacing = 12
    pressfit_hole_depth = 10  # for alignment pins
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
    tube_pocket_OD = tube_OD - 0.5  # for pressfit
    tube_clearance_OD = tube_OD*1.2  # to ensure the pusher downer doesn't get interfered with by the tube splooges
    tube_splooge = 0.5  # if the tube was unbotherd, its center point would cause this much overlap with the substrate

    # spring pin spacer parameters
    sp_spacer_encroachment = 2  # amount to encroach on the adapter board non-pin edges
    sp_spacer_encroachment_keepout = 6  # width of central keepout ear/zone
    sp_cut_ears = True  # true to cut ears to expose adapter board smt components
    sp_spacer_t = 1.20  # distance between the adapter and the substrate surface
    # such that pin 0921-1 has the correct remaining travel when in use. nominally, this remaining travel
    # would be 0.5mm and that corresponds to a spacer thickness here of 1.26mm, but a 1.2mm thick PCB is a good option
    sp_spacer_aux_pad_hole_d = 0  # for the holes that correspond to where the aux pads would be
    sp_spacer_aux_pin_clearance_d = 1.0  # for the holes above the connector pins

    # holder layer parameters
    holder_t = 3.5  # holder thickness, 2.2mm =thickest glass + pin travel
    holder_aux_con_d = 0.8  # diameter for the holes above the aux connection points
    crescent_angle = 270  # make crescents that enclose round things by this many degrees
    holder_corner_r = 1.0  # max cutting tool radius that can be used to mill the pockets
    crescent_opening_radial_fraction_offset = math.sin((360-crescent_angle)/2*math.pi/180)
    holder_aux_pad_hole_d = 0    # for the holes that correspond to where the aux pads would be
    holder_aux_pin_clearance_d = 1.0  # for the holes above the connector pins

    # multiply this by radius to get the distance between the center and the edge of the pocket

    # check splooge value
    max_splooge = tube_OD/2 - crescent_opening_radial_fraction_offset*tube_OD/2
    if (tube_splooge >= max_splooge):
        raise(ValueError("Too much tube splooge."))
    
    # pusher downer params
    pd_width_offset = 0.2  # come in this far on + and -X sides from the substrate edges
    pd_substrate_encroachment = 2.0  # enter the substrate area by this much, maximum
    pd_x_side_thickness = 9  # thickness on the x edges, more causes shadowing
    pd_y_side_thickness = 3  # thickness on the y edges, more causes shadowing
    pd_y_side_width = 15  # width of region where y side thickness is important
    pd_cut_tool_r_big = 2.5  # max radius of cutting tool that can be used to finish the big rounds
    pd_cut_tool_r_small = 1.5  # max radius of cutting tool that can be used to finish the small rounds
    pd_cut_tool_r_smaller = 1.0  # max radius of cutting tool that can be used to finish the smaller rounds
    pd_chamfer_l = 0.5  # chamfer edges for handling
    pd_tiny_chamfer_l = 0.04  # chamfer length for small holes spring pin passthroughs
    pd_pcb_mount_hole_r = tb.c.std_screw_threads['m2']["tap_r"]  # pusherdowner pcb mount hole radius
    pd_pcb_mount_hole_d = 4  # pusherdowner pcb mount hole depth
    pd_subs_alignment_z_allowance = 2  # allow space for the substrate alignment pins to be too long by this much
    pd_pcb_aux_mount_hole_offsets = (6, -12)  # for positioning the pcb mounting holes by the aux connections
    # (offset from x-pcb edges, offset from end of extra on +/-y side)
    pd_aux_pad_hole_d = 0  # for the holes that correspond to where the aux pads would be
    pd_aux_pin_clearance_d = sa_socket_hole_d  # for the holes above the connector pins
    # (actually only shows up in the top pcb) because they get cut off in the pusher downer

    # width of the top of the resulting countersink (everywhere, generally good for M5)
    csk_diameter = 11

    # radius on the above shelf fillet
    above_shelf_fr = 9

    # radius on the shelf fillet
    shelf_fr = above_shelf_fr

    shelf_height = 5 # thickness of the endblock shelves
    top_mid_height = 4.9+2.2+9.5-pcb_top_bump_up  # estimate TODO: double check this

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
    substrate_thickness_worst_case = 2.2  # used to decide where the  pusher downer should be drawn

    # should the bottom of the pcb slot passthroughs be rounded?
    round_slot_bottom = True  # false is probably impossible to machine (bit becomes too long and thin)

    # leave this much of a gap between the side pcb protection flaps and the main body
    protection_flap_offset_from_body = 1.0

    # fillet radius for the outer fillets
    outer_fillet = 3

    # chamfer length for the outer chamfers
    outer_chamfer = 0.5

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
        ln_pocket_move = lambda loc: CQ().box(tb.c.std_hex_nuts["m5"]["flat_w"]+0.1, tb.c.std_hex_nuts["m5"]["corner_w"]+0.1, self.eb_locknut_depth).translate((0,0,-self.eb_locknut_depth/2)).edges('|Z').fillet(2).findSolid().move(loc)
        endblock = endblock.faces('>Z[-2]').workplane(centerOption=co).center(0,self.pcb_cut_rad/2).cutEach(ln_pocket_move)

        # make a lock nut slot in the top base face
        endblock = endblock.faces('>Z[-1]').workplane(centerOption=co).cutEach(ln_pocket_move)

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

        one = 1  # extrude everything here to 1mm just so we can operate in 3D (output later will only be wires)
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
        row_centerg = c.mkgrid2d(self.period[0],1,self.array[0], 1)  # grid of row centers
        row_centerp = c.grid2dtolist(*row_centerg)   # list of row center points
        aux_pins_x_offset_from_edge = self.pcb_thickness/2+1
        aehg = c.mkgrid2d(self.substrate_adapters[0]-2*aux_pins_x_offset_from_edge, 2, 2, self.aux_pads_n)  # aux electrical connection point grid
        aepg = c.mkgrid2d(self.substrate_adapters[0]-2-4, 2, 2, self.aux_pads_n)  # aux electrical pad point grid
        aecy1 = aehg[1] + shelf_y_minus_center + self.aux_pad_center_shift  # y vales for the connection points & pads
        aecy2 = aehg[1] + shelf_y_plus_center - self.aux_pad_center_shift # y vales for the connection points & pads
        # do array of array to build up a list of the points for all the aux electrical hole and pad locations
        aehp = []
        aepp = []
        for row_center in row_centerp:
            aehp = aehp + c.grid2dtolist(aehg[0]+row_center[0], aecy1) + c.grid2dtolist(aehg[0]+row_center[0], aecy2)  # for connection points from crossbars
            aepp = aepp + c.grid2dtolist(aepg[0]+row_center[0], aecy1) + c.grid2dtolist(aepg[0]+row_center[0], aecy2)  # for associated pad points
        if aux_con_hole_d > 0:
            aehv = CQ().circle(aux_con_hole_d/2).extrude(one)  # for connection points from crossbars
            aehvs = CQ().pushPoints(aehp).eachpoint(lambda l: aehv.val().located(l))
            sand = sand.cut(aehvs)
        if aux_con_pad_hole_d > 0:
            aepv = CQ().circle(aux_con_pad_hole_d/2).extrude(one)  # for associated pad points
            aepvs = CQ().pushPoints(aepp).eachpoint(lambda l: aepv.val().located(l))
            sand = sand.cut(aepvs)

        return sand.faces("<Z[-1]").wires()

    def make_adapter_spacer(self, wp, cpg):
        """makes the substrate adapter spacer PCB"""
        co = "CenterOfBoundBox"
        c = type(self)  # this class

        # make adapter spacer basic shape
        adp_spc = CQ().add(self.make_sandwich_wires(wp, self.alignment_pin_clear_d, self.as_aux_pin_clearance_d, self.as_aux_pad_hole_d)).toPending().extrude(self.pcb_thickness)

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
        """builds a few of the tightly coupled sandwich layers given a working plane and substrate center point grid"""
        c = type(self)  # this class
        s = self
        co = "CenterOfBoundBox"

        if (s.substrate_spacing[0] >= 10) and (s.substrate_spacing[1] >= 10):
            many_pockets = True  # we have enough room to do pockets for every substrate
        else:
            many_pockets = False
        
        if (s.substrate_spacing[0] == 0) and (s.substrate_spacing[1] == 0):
            unipocket = True  # treat all the substrates as a unit, making one big holder pocket
        else:
            unipocket = False

        # spring pin spacer base
        sp_spc = CQ().add(s.make_sandwich_wires(wp,s.alignment_pin_clear_d, s.sp_spacer_aux_pin_clearance_d, s.sp_spacer_aux_pad_hole_d)).toPending().extrude(s.sp_spacer_t)
        sp_spc = sp_spc.edges('|Z').fillet(self.pcb_cut_rad)  # round the outside edges

        # make spring pin spacer layer windows
        spswv = (  # volume for a single window
            CQ().rect(s.substrate_adapters[0]+s.pcb_cut_rad, s.substrate_adapters[1]-2*s.sp_spacer_encroachment)
            .extrude(s.sp_spacer_t)
        )
        spswv = spswv.cut(
            CQ().rect(s.substrate_adapters[0]-2*s.sa_border_thickness[0], s.substrate_adapters[1]+s.pcb_cut_rad)
            .extrude(s.sp_spacer_t)
        )
        # come way in on the y edges
        spswv = spswv.edges('|Z').fillet(s.pcb_cut_rad)  # round the window edges
        spswv = spswv.union(
            CQ().rect(s.substrate_adapters[0], s.substrate_adapters[1]-2*s.sa_border_thickness[1])
            .extrude(s.sp_spacer_t)
        )
        # but leave ears for the smt parts on the adapters (TODO: this creates impossible geometry for zero spacing case)
        spswv = spswv.edges('|Z').fillet(s.pcb_cut_rad)  # round the window edges
        if s.sp_cut_ears:
            spswv = spswv.union(
                CQ().rect(s.sp_spacer_encroachment_keepout, s.substrate_adapters[1])
                .extrude(s.sp_spacer_t)
                .edges('|Z').fillet(s.pcb_cut_rad)
            )

        cps = c.grid2dtolist(*cpg)  # list of center points for substrates
        spswvs = CQ().pushPoints(cps).eachpoint(lambda l: spswv.val().located(l))
        sp_spc = sp_spc.cut(spswvs)  # cut out the windows

        # generate the sample holder base
        sh = CQ().add(s.make_sandwich_wires(wp, s.alignment_pin_slide_d, s.holder_aux_pin_clearance_d, s.holder_aux_pad_hole_d)).toPending().extrude(s.holder_t)
        sh = sh.edges('|Z').fillet(self.pcb_cut_rad)  # round the outside edges

        # calculate width of extra pocket space that the crescent design feature gives us
        pocket_extra_tube_side = s.tube_pocket_OD/2*(1-s.crescent_opening_radial_fraction_offset)
        pocket_extra_pin_side = s.sapd_press/2*(1-s.crescent_opening_radial_fraction_offset)

        # calculate points for the pocket corner rounding drills (as offset from nominal substrate corner location)
        round_offset_pin_side = pocket_extra_pin_side - s.holder_corner_r*1/math.sqrt(2)
        round_offset_tube_side = pocket_extra_tube_side - s.holder_corner_r*1/math.sqrt(2)

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

            # generate one substrate holder base pocket shape
            hp = CQ().box(s.substrate_adapters[0], s.substrate_adapters[1], s.holder_t, centered=(True, True, False))

            # calculate the drill points for rounding the substrate pocket corners
            pcgx1 = cpg[0] - s.substrate_adapters[0]/2 - round_offset_pin_side
            pcgx2 = pcgx1
            pcgx3 = cpg[0] + s.substrate_adapters[0]/2 + round_offset_tube_side
            pcgx4 = pcgx3
            pcgy1 = cpg[1] - s.substrate_adapters[1]/2 - round_offset_pin_side
            pcgy2 = cpg[1] + s.substrate_adapters[1]/2 + round_offset_tube_side
            pcgy3 = pcgy1
            pcgy4 = pcgy2
            pcps = (  # pocket corner drill rounding point list
                c.grid2dtolist(pcgx1,pcgy1) +
                c.grid2dtolist(pcgx2,pcgy2) +
                c.grid2dtolist(pcgx3,pcgy3) +
                c.grid2dtolist(pcgx4,pcgy4)
            )

        elif unipocket == True:
            # calculate substrate alignment pin locations
            x1 = -s.substrate_adapters[0]*s.array[0]/2-s.sapd/2
            x2 = -s.substrate_adapters[0]*s.array[0]/2-s.sapd/2
            x3 = -s.substrate_adapters[0]*s.array[0]*s.sap_offset_fraction
            x4 =  s.substrate_adapters[0]*s.array[0]*s.sap_offset_fraction

            y1 =  s.substrate_adapters[1]*s.array[1]*s.sap_offset_fraction
            y2 = -s.substrate_adapters[1]*s.array[1]*s.sap_offset_fraction
            y3 = -s.substrate_adapters[1]*s.array[1]/2-s.sapd/2
            y4 = -s.substrate_adapters[1]*s.array[1]/2-s.sapd/2

            # generate substrate alignment pin points list
            apps = [
                (x1, y1),
                (x2, y2),
                (x3, y3),
                (x4, y4),
            ]

            # calculate squishy tube centers
            tx1 = 0
            tx2 = s.substrate_adapters[0]*s.array[0]/2 + s.tube_OD/2 - s.tube_splooge
            ty1 = s.substrate_adapters[1]*s.array[1]/2 + s.tube_OD/2 - s.tube_splooge
            ty2 = 0

            # generate the tube hole center points list
            tps = [
                (tx1,ty1),
                (tx2,ty2),
            ]

            # generate a uni substrate holder pocket
            hp = CQ().box(s.substrate_adapters[0]*s.array[0], s.substrate_adapters[1]*s.array[1], s.holder_t, centered=(True, True, False))

            # calculate the drill points for rounding the substrate pocket corners
            pcgx1 = -s.substrate_adapters[0]*s.array[0]/2 - round_offset_pin_side
            pcgx2 = pcgx1
            pcgx3 =  s.substrate_adapters[0]*s.array[0]/2 + round_offset_tube_side
            pcgx4 = pcgx3
            pcgy1 = -s.substrate_adapters[1]*s.array[1]/2 - round_offset_pin_side
            pcgy2 =  s.substrate_adapters[1]*s.array[1]/2 + round_offset_tube_side
            pcgy3 = pcgy1
            pcgy4 = pcgy2
            pcps = [  # pocket corner drill rounding point list
                (pcgx1,pcgy1),
                (pcgx2,pcgy2),
                (pcgx3,pcgy3),
                (pcgx4,pcgy4),
            ]

        # enlarge the holder pockets as allowed by the registration hardware
        hp = hp.faces("<Y[-1]").wires().toPending().workplane().extrude(pocket_extra_pin_side)
        hp = hp.faces(">Y[-1]").wires().toPending().workplane().extrude(pocket_extra_tube_side)
        hp = hp.faces("<X[-1]").wires().toPending().workplane().extrude(pocket_extra_pin_side)
        hp = hp.faces(">X[-1]").wires().toPending().workplane().extrude(pocket_extra_tube_side)
        if many_pockets == True:
            hps = s.replicate(hp, cpg)
        elif unipocket == True:
            hps = hp

        # make one substrate alignment pin hole volume for the spring pin spacer layer
        aphv = CQ().circle(s.sapd/2).extrude(s.sp_spacer_t+1).translate((0,0,-0.5))  # this works around a bug in step file export
        # see https://github.com/CadQuery/cadquery/issues/697
        #aphv = CQ().circle(s.sapd/2).extrude(s.sp_spacer_t)  # this line should look like this
        aphhv = CQ().circle(s.sapd_press/2).extrude(s.holder_t)
        aphvs  = CQ().pushPoints(apps).eachpoint(lambda l:  aphv.val().located(l))  # replicate that
        aphhvs = CQ().pushPoints(apps).eachpoint(lambda l: aphhv.val().located(l))  # replicate that
        
        # make one tube clearance hole volume for the spring pin spacer layer
        thv =  CQ().circle(s.tube_OD/2).extrude(s.sp_spacer_t)
        thhv = CQ().circle(s.tube_pocket_OD/2).extrude(s.holder_t)
        thvs =  CQ().pushPoints(tps).eachpoint(lambda l:  thv.val().located(l))  # replicate that
        thhvs = CQ().pushPoints(tps).eachpoint(lambda l: thhv.val().located(l))  # replicate that

        # make one holder pocket corner rounding cylinder
        hpcv = CQ().circle(s.holder_corner_r).extrude(s.holder_t)
        hpcvs = CQ().pushPoints(pcps).eachpoint(lambda l: hpcv.val().located(l))  # replicate that

        # cut out substrate alignment pin hole volumes
        sp_spc = sp_spc.cut(aphvs)
        sh     =     sh.cut(aphhvs)

        # cut out the tube hole volumes
        sp_spc = sp_spc.cut(thvs )
        sh     =     sh.cut(thhvs)

        # round the corners for the holder pockets(s)
        sh = sh.cut(hpcvs)

        # cut out the holder pocket(s)
        sh = sh.cut(hps.edges('|Z').chamfer(s.holder_corner_r))  # need to chamfer here to avoid OCCT bug

        # generate the pusher downer base shape
        pd = CQ().add(s.make_sandwich_wires(wp, s.alignment_pin_slide_d, s.pd_aux_pin_clearance_d, s.pd_aux_pad_hole_d)).toPending().extrude(s.pd_x_side_thickness)

        # now remove some area so it can push down
        pd_edge = pd.faces('<Z[-1]').edges('%LINE').vals()
        del_vol = CQ().add(cq.Wire.assembleEdges(pd_edge)).toPending().extrude(s.holder_t)
        del_vol = del_vol.rarray(s.period[0], s.period[1], s.array[0], s.array[1]).rect(s.substrate_adapters[0], s.substrate_adapters[1]).cutThruAll()
        pd = pd.cut (del_vol)

        # cut the windows
        pd = pd.rarray(s.period[0], s.period[1], s.array[0], s.array[1]).rect(s.substrate_adapters[0]-2*s.pd_substrate_encroachment, s.substrate_adapters[1]-2*s.pd_substrate_encroachment).cutThruAll()

        # slice out one col and center it if needed
        slicer = CQ().center(0,-s.extra[2]).box(s.substrate_adapters[0]-2*s.pd_width_offset, s.extra[2]+s.extra[3]+s.period[1]*s.array[1]*2, s.pd_x_side_thickness, centered=(True, True, False))
        if self.array[0]%2 == 1:
            translation = (0, 0, 0)
        else:  # even number of cols
            translation = (s.period[0]/2, 0, 0)
        pd = pd.translate(translation).intersect(slicer)

        # save the wires we'll use to construct the top PCB
        top_pcb_wires = pd.translate((0,0,-s.pd_x_side_thickness)).faces('>Z[-1]').wires().vals()

        # cut the edges on the ends to allow for the aux connections
        pd = (
            pd.faces('<Y[-1]').workplane(centerOption=co)
            .pushPoints([(-s.substrate_adapters[0]/2, 0), (s.substrate_adapters[0]/2, 0)])
            .rect(4+s.pcb_thickness, s.pd_x_side_thickness)
            .cutBlind(-s.aux_pads_n*2)
        )

        pd = (
            pd.faces('>Y[-1]').workplane(centerOption=co)
            .pushPoints([(-s.substrate_adapters[0]/2, 0), (s.substrate_adapters[0]/2, 0)])
            .rect(4+s.pcb_thickness, s.pd_x_side_thickness)
            .cutBlind(-s.aux_pads_n*2)
        )

        # cut the y-side shadow preventor dent(s)
        if unipocket == True:
            dent_y_l = s.array[1]*s.substrate_adapters[1]
            n_dent_y = 1
        elif many_pockets == True:
            dent_y_l = s.substrate_adapters[1]
            n_dent_y = s.array[1]
        dentv = CQ().box(s.pd_y_side_width, dent_y_l, s.pd_x_side_thickness-s.pd_y_side_thickness, centered=(True, True, False))
        dentvs = CQ().rarray(s.period[0], s.period[1], s.array[0], n_dent_y).eachpoint(lambda l: dentv.val().located(l))  # replicate that
        dentvs = dentvs.edges('|Z').fillet(s.pd_cut_tool_r_big)  # round for manufacturability
        pd = pd.cut(dentvs.translate((translation[0], 0, s.pd_y_side_thickness)))

        # select edges to round by z position
        #pd = CQ().add(pd.findSolid()).edges('<Z[-1] or <Z[-3] or <Z[-4] or <Z[-5]').fillet(0.6)  #use this radius to explore the edge heights if needed
        # -1 is the level of the edges of the bottom pusher(s)
        # -2 is the level of the tiny edges in the y shadow preventor dents
        # -3 is the level of the edges of the window inner
        # -4 is the level of the edges of the y shadow preventor dent
        # -5 is the level of the edges of the outermost edges
        pd = CQ().add(pd.findSolid()).edges('<Z[-5] except (<<Y or >>Y)').fillet(s.pd_cut_tool_r_smaller)  # shoulder edges
        pd = CQ().add(pd.findSolid()).edges('<Z[-1] or <Z[-3] or <Z[-5]').fillet(s.pd_cut_tool_r_big)

        if unipocket == True:  # in manypocket case, this is handled by the negative dent shape's round
            pd = pd.edges('<Z[-4]').fillet(s.pd_cut_tool_r_small)

        # chamfer outer edges for improved hand friendliness
        if unipocket == True:  # BUG in OCCT makes nonsense geometry here except in unipocket case
            pd = pd.faces('<Z[-1]').edges().chamfer(s.pd_chamfer_l)  # bottom edges 
        pd = pd.faces('<Z[-3]').edges('<Y or >Y or <X or >X').chamfer(s.pd_chamfer_l)  # "middle" edges
        pd = pd.faces('>Z[-1]').edges('not(%CIRCLE)').chamfer(s.pd_chamfer_l)  # top edges

        # chamfer the big holes for ease of assembly/alignment
        pd = pd.edges('%CIRCLE').edges('<<Y[-3]').chamfer(s.pd_chamfer_l)  # three in line holes at one end
        pd = pd.edges('%CIRCLE').edges('>>Y[-3]').chamfer(s.pd_chamfer_l)  # three in line holes at the other end

        # now we remove material so that the pusher doesn't bother the squishy tubes and the substrate alignment pins
        # make one hole volume for alignment pin clearance
        apphv = CQ().circle(s.sapd_clear/2).extrude(s.pd_x_side_thickness).translate((0, 0, -s.pd_x_side_thickness+s.holder_t+s.pd_subs_alignment_z_allowance))
        apphvs = CQ().pushPoints(apps).eachpoint(lambda l:  apphv.val().located(l))  # replicate that
        # make the tube clearance volumes, translated properly in z so they can only cut the bottom pusher part
        tphv =  CQ().circle(s.tube_clearance_OD/2).extrude(s.pd_x_side_thickness).translate((0, 0, -s.pd_x_side_thickness+s.holder_t))
        tphvs =  CQ().pushPoints(tps).eachpoint(lambda l:  tphv.val().located(l))  # replicate that
        all_cut = CQ().add(apphvs.vals()).add(tphvs.vals())  # unify the things we want to cut so we can do it in one step
        if many_pockets == True:
            # drill the alignment pin and sube clearance holes (translating the part, then untranslating if needed)
            pd = pd.translate((translation[0]*-1, 0, 0))  # make sure the part is in its "native" home
            pd = pd.cut(all_cut)
            pd = pd.translate(translation)  # put the part back into its non-native, centered spot (if needed)
        elif unipocket == True:
            # step the piece through all possible positions and subtract whatever intersects at each location
            # this ensures the pusher isn't unique to a specific slot
            ip = c.grid2dtolist(*c.mkgrid2d(s.period[0],1,s.array[0],1))  # install points
            for point in ip:
                # translate --> cut --> untranslate, for each possible install position
                pd = (
                    CQ().add(pd.findSolid())
                    .translate((point[0], 0 ,0))
                    .cut(all_cut)
                    .translate((-point[0], 0 ,0))
                )

        # top pcb mounting holes
        # the per-substrate ones
        pdpmhg = c.mkgrid2d(2*s.sap_offset_fraction*s.substrate_adapters[0],s.period[1], 2, s.array[1])
        pdpmhp = c.grid2dtolist(pdpmhg[0], pdpmhg[1]+s.substrate_adapters[1]/2)
        # ones next to the aux connections
        pdpmhp.append(( s.substrate_adapters[0]/2-s.pd_pcb_aux_mount_hole_offsets[0],  s.array[1]*s.period[1]/2+s.extra[3]+s.pd_pcb_aux_mount_hole_offsets[1]))
        pdpmhp.append((-s.substrate_adapters[0]/2+s.pd_pcb_aux_mount_hole_offsets[0],  s.array[1]*s.period[1]/2+s.extra[3]+s.pd_pcb_aux_mount_hole_offsets[1]))
        pdpmhp.append(( s.substrate_adapters[0]/2-s.pd_pcb_aux_mount_hole_offsets[0], -s.array[1]*s.period[1]/2-s.extra[2]-s.pd_pcb_aux_mount_hole_offsets[1]))
        pdpmhp.append((-s.substrate_adapters[0]/2+s.pd_pcb_aux_mount_hole_offsets[0], -s.array[1]*s.period[1]/2-s.extra[2]-s.pd_pcb_aux_mount_hole_offsets[1]))

        # one hole volume
        pdpmhv = CQ().circle(s.pd_pcb_mount_hole_r).extrude(s.pd_pcb_mount_hole_d).translate((0,0,-s.pd_pcb_mount_hole_d))
        pdpmhvs = CQ().pushPoints(pdpmhp).eachpoint(lambda l:  pdpmhv.val().located(l))  # replicate that

        pd = pd.cut(pdpmhvs.translate((0, 0, s.pd_x_side_thickness)))
        # pusher downer done

        # make the top PCB bulk
        top_pcb = CQ().add(top_pcb_wires).toPending().extrude(s.pcb_thickness)

        # cut the top pcb mounting holes
        tpmhv = CQ().circle(tb.c.std_screw_threads['m2']['clearance_r']).extrude(s.pcb_thickness)
        tpmhvs = CQ().pushPoints(pdpmhp).eachpoint(lambda l:  tpmhv.val().located(l))  # replicate that
        top_pcb = top_pcb.cut(tpmhvs)
        # top PCB done

        return sp_spc, sh, pd, top_pcb

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
        self.pcb_extension_fudge = round(math.ceil(extension_length/0.25)*0.25-extension_length,2)

        # fudge extension length to get it on mm grid
        self.extension_length = round(extension_length + self.pcb_extension_fudge, 2)

        # the amount beyond the normal chamber dims needed to protect the crossbar pcbs
        self.crossbar_chamber_extra = extension_length - self.endblock_wall_spacing - self.wall[2]

        # extend for external connectors
        crossbar = (
            CQ(innter_crossbar.findSolid())
            .faces("<Y[-1]").wires().toPending().workplane().extrude(extension_length)
        )

        # fillet the edges fails now because of one place and so we won't do it here
        #crossbar = crossbar.edges('|X').fillet(self.pcb_cut_rad)

        return(crossbar.translate((-self.pcb_thickness/2, 0, 0)))

    def make_crossbars(self, crossbar):
        """replicate the crossbars"""
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
        s = self  # my instance
        c = type(self)  # my class
        co = "CenterOfBoundBox"

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

        # add features for PCB protection
        # extend the top
        top = top.faces("<Y[-1]").wires().toPending().workplane().extrude(s.crossbar_chamber_extra)
        # give the extended top protection flaps
        top = (
            CQ().add(top.findSolid()).faces('<Z[-1]').workplane()
            # y values are inverted becuse we're downsideup
            .moveTo(srbb.xmin, -srbb.ymin+s.protection_flap_offset_from_body)
            .rect(s.wall[0], s.crossbar_chamber_extra - s.protection_flap_offset_from_body, centered=(False,False))
            .extrude(s.wall_height+s.shelf_height)
            .moveTo(srbb.xmax-s.wall[1], -srbb.ymin+s.protection_flap_offset_from_body)
            .rect(s.wall[1], s.crossbar_chamber_extra - s.protection_flap_offset_from_body, centered=(False,False))
            .extrude(s.wall_height+s.shelf_height)
        )

        # cut the v potting groove for the potting between the pieces
        pg = tb.groovy.mk_vgroove(pot_slot_path, (srbb.xmin + s.wall[0] - s.pg_offset, 0, 0), s.pg_depth)
        middle = middle.cut(pg)

        # gas feedthroughs
        if s.do_gas_feedthroughs == True:
            middle = middle.faces('<X[-1]').workplane(origin=(0, 0, -s.pcb_top_bump_up-s.wall_height/2)).circle(s.feedthrough_d/2).cutThruAll()
        
        # fillet some Z lines and chamfer x-y ones for handling/beauty
        middle = CQ().add(middle.findSolid()).edges('|Z').edges('>>Y[-1]').fillet(s.outer_fillet)
        top =    CQ().add(top   .findSolid()).edges('|Z').edges('>>X[-1] or <<X[-1]').edges('>>Y[-1] or <<Y[-1]').fillet(s.outer_fillet)

        middle = middle.faces('<Z[-1]').edges('not %CIRCLE').chamfer(s.outer_chamfer)
        top = top.faces('>Z[-1] or <Z[-1] or <Y[-1]').edges().chamfer(s.outer_chamfer)
        #top = top.faces('<Y[-1]').edges('not >Z[-1]').chamfer(s.outer_chamfer)
        #top =    CQ().add(top   .findSolid()).edges('|Z').edges('<<Y[-1]').fillet(s.outer_fillet)

        return (middle, top)  # clean() to remove unwanted lines in faces

    def build(self):
        s = self
        c = type(self)  # my class
        asy = cadquery.Assembly()

        # the device plane
        werkplane = self.make_plane()
        asy.add(werkplane, name="werkplane")

        # generate a crossbar PCB core (needed for outline export) 
        crossbar = self.make_crossbar(werkplane)
        
        # make the middle pieces
        middle, top_mid= self.make_middle(werkplane)
        asy.add(middle.translate((0,0,self.woff)), name="middle", color=cadquery.Color("orange"))
        asy.add(top_mid.translate((0,0,self.woff)), name="top_mid", color=cadquery.Color("yellow"))

        # replicate the crossbar
        crossbars = self.make_crossbars(crossbar)
        asy.add(crossbars, name="crossbars", color=cadquery.Color("darkgreen"))

        endblock = self.make_endblock()
        endblocks = self.make_endblocks(endblock, werkplane)
        asy.add(endblocks, name="endblocks", color=cadquery.Color("gray"))

        # generate the substrate center grid
        cpg = self.find_substrate_grid()

        substrate = CQ().rect(*self.substrate_adapters).extrude(self.substrate_thickness)
        substrates = self.replicate(substrate, cpg).translate((0, 0, self.pcb_thickness+self.sp_spacer_t))
        #asy.add(substrates.translate((0,0,4)), name="substrates", color=cadquery.Color("lightblue"), alpha=0.4)
        # should be "lightblue" with alpha = 0.3 but alpha is broken?
        asy.add(substrates, name="substrates", color=cadquery.Color(107/255,175/255,202/255,0.3))

        adapter = self.make_adapter()
        adapters = self.replicate(adapter, cpg)
        asy.add(adapters, name="adapters", color=cadquery.Color("darkgreen"))

        adapter_spacer = self.make_adapter_spacer(werkplane, cpg)
        asy.add(adapter_spacer, name="adapter_spacer", color=cadquery.Color("darkgreen"))

        spring_pin_spacer, substrate_holder, pusher_downer, top_pcb = self.make_some_layers(werkplane, cpg)
        pusher_downers = self.replicate(pusher_downer, c.mkgrid2d(self.period[0], 1, self.array[0], 1))
        top_pcbs = self.replicate(top_pcb, c.mkgrid2d(self.period[0], 1, self.array[0], 1))
        asy.add(spring_pin_spacer.translate((0, 0, self.pcb_thickness)), name="spring_pin_spacer", color=cadquery.Color("black"))
        asy.add(substrate_holder.translate((0, 0, self.pcb_thickness+self.sp_spacer_t)), name="substrate_holder", color=cadquery.Color("red"))
        asy.add(pusher_downers.translate((0, 0, self.pcb_thickness+self.sp_spacer_t+self.substrate_thickness_worst_case)), name="pusher_downers", color=cadquery.Color("brown"))
        asy.add(top_pcbs.translate((0, 0, self.pcb_thickness+self.sp_spacer_t+self.substrate_thickness_worst_case+self.pd_x_side_thickness)), name="top_pcbs", color=cadquery.Color("darkgreen"))

        return (asy, crossbar, adapter, adapter_spacer, spring_pin_spacer, substrate_holder, pusher_downer, top_pcb)

def main():
    #s = ChamberNG(array=(1, 1), subs =(30, 30), spacing=(10, 10), padding=(5,5,0,0))
    s = ChamberNG(array=(1, 4), subs =(30, 30), spacing=(10, 10), padding=(5,5,0,0))
    #s = ChamberNG(array=(4, 4), subs =(30, 30), spacing=(10, 10), padding=(5,5,0,0))
    #s = ChamberNG(array=(5, 5), subs =(30, 30), spacing=(0, 0), padding=(10,10,5,5))
    (asy, crossbar, adapter, adapter_spacer, spring_pin_spacer, substrate_holder, pusher_downer, top_pcb) = s.build()
    
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

        save_indivitual_stls = False
        save_indivitual_steps = False

        if (save_indivitual_stls == True) or (save_indivitual_steps == True):
            # loop through individual pieces STLs
            for key, val in asy.traverse():
                shapes = val.shapes
                if shapes != []:
                    c = cq.Compound.makeCompound(shapes)
                    if save_indivitual_stls == True:
                        if val.name == 'pusher_downers':
                            cadquery.exporters.export(pusher_downer.findSolid().locate(val.loc), 'pusher_downer.stl')
                        cadquery.exporters.export(c.locate(val.loc), f'{val.name}.stl')
                    if save_indivitual_steps == True:
                        if val.name == 'pusher_downers':
                            cadquery.exporters.export(pusher_downer.findSolid().locate(val.loc), 'pusher_downer.step')
                        cadquery.exporters.export(c.locate(val.loc), f'{val.name}.step')
        
        # save DXFs
        crossbar_outline = CQ().add(crossbar.rotate((0,0,0),(0,1,0),-90).rotate((0,0,0),(0,0,1),-90)).section()
        cadquery.exporters.exportDXF(crossbar_outline, 'crossbar_outline.dxf')

        adapter_outline = adapter.section()
        cadquery.exporters.exportDXF(adapter_outline, 'adapter_outline.dxf')

        adapter_spacer_outline = CQ().add(adapter_spacer.findSolid()).section()  # add to new wp to fix orientation
        cadquery.exporters.exportDXF(adapter_spacer_outline, 'adapter_spacer_outline.dxf')

        spring_pin_spacer_outline = spring_pin_spacer.section()
        cadquery.exporters.exportDXF(spring_pin_spacer_outline, 'spring_pin_spacer_outline.dxf')

        substrate_holder_outline = substrate_holder.section()
        cadquery.exporters.exportDXF(substrate_holder_outline, 'substrate_holder_outline.dxf')

        top_pcb_outline = top_pcb.section()
        cadquery.exporters.exportDXF(top_pcb_outline, 'top_pcb_outline.dxf')

main()
