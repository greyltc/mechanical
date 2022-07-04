import math
from re import S
from cadquery import cq, CQ
import cadquery
from . import utilities as u
from . import constants as c
from . import groovy
import logging
from cq_warehouse.fastener import CounterSunkScrew, PanHeadScrew
import cq_warehouse.extensions  # this does something even though it's not directly used

"""
cuts a pcb card edge passthrough through something
along the Z direction
"""

# setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(("%(asctime)s|%(name)s|%(levelname)s|" "%(message)s"))
ch.setFormatter(formatter)
logger.addHandler(ch)

# length of the connector passthrough geometry on the bottom surface
surface_length: float = None  # type: ignore[assignment]


def make_oringer(
    self: cq.Workplane,
    board_width: float = 84.12,
    board_inner_depth: float = 9.271,
    board_outer_depth: float = 9.271,
    part_thickness: float = 0,
    wall_depth: float = 0,
    screw="M3-0.5",
    pt_asy: cadquery.Assembly = None,
    pcb_asy: cadquery.Assembly = None,
    hw_asy: cadquery.Assembly = None,
) -> cq.Workplane:
    logger = logging.getLogger(__name__)
    if wall_depth == 0:  # if depth is not given do our best to find it
        wall_depth = u.find_length(self, along="normal", bb_method=False)
    if part_thickness == 0:  # if thickness is not given, use half the wall thickness
        part_thickness = wall_depth / 2

    pcbt = 1.6  # pcb thickness
    washert = 0.5  # washer thickness

    screw_nominal_d = 3
    screw_head_nominal_d = 6

    # header specific for making the pin0 holes, probably doesn't belong here, but it's too convenient...
    non_notch_side_chunk_width = 0.381  # is 0.15 in
    non_chunk_con_width = 8.89  # is 0.35 in
    pin0_offsetx = non_chunk_con_width / 2 + non_notch_side_chunk_width + 2.54 / 2
    pin0_offsety_25 = 2.54 * (25 - 1) / 2
    pin0_offsety_20 = 2.54 * (20 - 1) / 2
    pin0_holed = 1

    p0pts = []  # the pin pin 1 points for the two connectors (for checking the correctness of the PCB designs)
    p0pts.append((pin0_offsety_25, pin0_offsetx))
    p0pts.append((-pin0_offsety_20 + 2.5 * 2.54, -(wall_depth + pin0_offsetx)))

    block_width = 7
    block_height_nominal = 6
    support_block = (block_width, block_height_nominal - washert)  # actual support block (leaves room for washer)

    pcb_corner = 2
    pt_pcb_mount_hole_offset = (4.445, block_width / 2)  # from corners

    pcb_scr_len = 12  # SHP-M3-12-V2-A2, round(block_height_nominal + pcbt + 4)
    pt_fix_scr_len = 10  # SHK-M3-10-V2-A2, round(wall_depth * 0.8)
    pt_fix_wall_buffer = 1  # amount of wall to leave behind the threaded screw hole
    fix_scr = CounterSunkScrew(size=screw, fastener_type="iso14581", length=pt_fix_scr_len)
    pcb_scr = PanHeadScrew(size=screw, fastener_type="iso14583", length=pcb_scr_len)
    # washer = CheeseHeadWasher(size=screw, fastener_type="iso7092")
    # nylock nut = HNN-M3-A2

    oring_cs = 1  # oring thickness

    min_radius = oring_cs * 3  # min inner bend radius
    min_wall = 0.8  # walls should not be mfg'd thinner than this

    min_gap = 0.25  # cutting tolerances prevent smaller gaps between things

    gland_width = groovy.get_gland_width(oring_cs)
    # effective_gland_width = (round(gland_width * 100) + 1) / 100  # rounded up to the nearest 0.01mm
    # logger.info(f"Using {effective_gland_width=}")

    # some important radii for construction to ensure we don't overbend the o-ring
    minr1 = min_radius - min_wall
    minr2 = min_radius + min_wall + gland_width

    # actual support block centers
    sbpts = []
    sbx = board_width / 2 - block_width / 2
    sby = ((-pcbt / 2 - washert) + (-pcbt / 2 - block_height_nominal)) / 2
    sbpts.append((sbx, sby))
    sbpts.append((-sbx, sby))

    in_off = minr1 * 2**-0.5 - min_gap * 2**0.5 / 2  # exact inward offset to get min_gap spacing with minr1 fillets

    ffo = minr1 * (1 - 2**-0.5) + min_gap * (2**0.5 / 2)
    co_tw = minr1 * 2 + min_gap  # width of the thin part of the cutout (so that the cutting tool can easily fit)
    max_slot_y = ffo + pcbt + block_height_nominal + ffo  # width at the slot at its max
    if co_tw > max_slot_y:
        co_tw = max_slot_y

    scy = -pcbt / 2 - block_height_nominal + in_off  # y coordinate for the inner, small radius circle
    scx = board_width / 2 - block_width + in_off  # small, inner circle x value

    tcy = pcbt / 2 - in_off  # top circles center y value
    tcx = board_width / 2 - in_off  # top circles center c values
    tcpts = []  # top circle points
    tcpts.append((tcx, tcy))
    tcpts.append((-tcx, tcy))

    ocpts1 = []  # outer circle points for positive x
    ocpts1.append((tcx, tcy))
    ocpts1.append((tcx, scy))

    ocpts2 = []  # outer circle points for negative x
    ocpts2.append((-tcx, tcy))
    ocpts2.append((-tcx, scy))

    bcpts1 = []  # bottom circle points for positive x
    bcpts1.append((tcx, scy))
    bcpts1.append((scx, scy))

    bcpts2 = []  # bottom circle points for negative x
    bcpts2.append((-tcx, scy))
    bcpts2.append((-scx, scy))

    icpts1 = []  # inner circle points for positive x
    icpts1.append((scx, scy))
    icpts1.append((scx, tcy))

    icpts2 = []  # inner circle points for negative x
    icpts2.append((-scx, scy))
    icpts2.append((-scx, tcy))

    swp = CQ().sketch()

    # need support block shapes to fill in gaps
    swp.push(sbpts).rect(*support_block)

    # the fillets at the bottom collide and should be unified with a circle, but the ones at the sides don't
    if (2 * minr1 > 2 * ffo + block_width) and (2 * minr1 < max_slot_y):
        scx = board_width / 2 - block_width / 2  # new center point for circles
        tcpts = []  # top circle points
        tcpts.append((scx, tcy))
        tcpts.append((-scx, tcy))

        ocpts1 = []  # outer circle points for positive x
        ocpts1.append((scx, tcy))
        ocpts1.append((scx, scy))

        ocpts2 = []  # outer circle points for negative x
        ocpts2.append((-scx, tcy))
        ocpts2.append((-scx, scy))

        # make the right circle hull
        swp.push(ocpts1).circle(minr1, mode="c", tag="c").reset().edges(tag="c").hull().clean().reset()

        # make the left circle hull
        swp.push(ocpts2).circle(minr1, mode="c", tag="d").reset().edges(tag="d").hull().clean().reset()

    # the fillets at the side collide and should be unified with a circle
    elif 2 * minr1 >= max_slot_y:
        cpts = []  # center points for new circles
        scy = (pcbt / 2 + (-pcbt / 2 - block_height_nominal)) / 2
        tcpts = []  # top circle points
        tcpts.append((tcx, scy))
        tcpts.append((-tcx, scy))

    # normal case, no fillets collide
    else:
        # make the right outer circle hull
        swp.push(ocpts1).circle(minr1, mode="c", tag="c").reset().edges(tag="c").hull().clean().reset()

        # make the left outer circle hull
        swp.push(ocpts2).circle(minr1, mode="c", tag="d").reset().edges(tag="d").hull().clean().reset()

        # make the right bottom circle hull
        swp.push(bcpts1).circle(minr1, mode="c", tag="e").reset().edges(tag="e").hull().clean().reset()

        # make the left bottom circle hull
        swp.push(bcpts2).circle(minr1, mode="c", tag="f").reset().edges(tag="f").hull().clean().reset()

    bcy = pcbt / 2 + ffo - (co_tw + minr2)  # y coordinate for the large radius circle

    # make the top circle hull
    swp.push(tcpts).circle(minr1, mode="c", tag="g").reset().edges(tag="g").hull().clean().reset()

    # do all the big circle stuff only if the outer fillets haven't merged
    if not (2 * minr1 > max_slot_y):
        o = scy - bcy  # opposite triangle side length (along y)
        h = minr2 + minr1  # hypotenuse
        if o < 0:  # the circles have moved apart: big one above small one (and the trig breaks)
            a = h
        elif o > h:  # the circles have moved apart (and the trig breaks)
            a = h  # adjacent (along x)
        else:
            a = h * math.cos(math.asin(o / h))
            # a = o/math.tan(math.asin(o/h))  # adjacent (along x)
        bcx = scx - a  # big circle x
        # bcy = pcbt/2+ffo-(co_tw+minr2)
        bcpts = []
        bcpts.append((-bcx, bcy))
        bcpts.append((bcx, bcy))

        swp.push([(-scx, scy), (scx, scy)]).circle(minr1).clean().reset()

        if o < 0:  # the circles have moved apart: big one above small one
            scy = bcy
            if 2 * minr1 < 2 * ffo + block_width:  # the bottom fillets haven't merged
                # make the left inner circle hull
                swp.push(icpts1).circle(minr1, mode="c", tag="h").reset().edges(tag="h").hull().clean().reset()
                # make the right inner circle hull
                swp.push(icpts2).circle(minr1, mode="c", tag="i").reset().edges(tag="i").hull().clean().reset()

        swp.polygon([(-bcx, bcy), (bcx, bcy), (scx, scy), (scx, 0), (-scx, 0), (-scx, scy), (-bcx, bcy)]).clean().reset()

        swp.push(bcpts).circle(minr2, mode="s").clean().reset()  # cut away the large circles

        swp.push([(0, bcy)]).rect(2 * bcx, minr2 * 2, mode="s").clean().reset()  # cut away the space between the circles

    through_face = swp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the through cut

    swp = swp.wires().offset(min_wall + gland_width / 2).clean().reset()  # inner edge of ogland
    o_face = swp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the oring path wire

    # passthrough face
    pfw = min_wall + gland_width + min_wall + ffo + board_width + ffo + min_wall + gland_width + min_wall  # passthrough face width
    pfha = min_wall + gland_width + min_wall + screw_nominal_d + (screw_head_nominal_d / 2 - screw_nominal_d / 2) + min_wall  # passthrough face height above cutout top edge
    pfhb1 = co_tw + min_wall + gland_width + min_wall + screw_nominal_d + (screw_head_nominal_d / 2 - screw_nominal_d / 2) + min_wall  # passthrough face height below cutout top edge
    pfhb2 = ffo + pcbt + block_height_nominal + ffo + min_wall + gland_width + min_wall  # passthrough face height below cutout top edge if limited by support block clearance
    if pfhb2 > pfhb1:  # if the part below the support blocks would be lower, use that to determine the face height
        pfhb = pfhb2
    else:
        pfhb = pfhb1
    pfha_pcb = pfha + pcbt / 2 + ffo  # passthrough face height above PCB middle
    pfh = pfha + pfhb  # passthrough face height
    pfx = 0
    pfy = -pfh / 2 + pfha_pcb
    pf_ctr = (pfx, pfy)  # passthrough face center
    pfdim = (pfw, pfh)  # passthrough face dims
    pf_fillets = 5  # fillets to corners of passthrough face
    pfwp = CQ().sketch()  # make passthrough face sketch workplane
    pfwp = pfwp.push([pf_ctr]).rect(*pfdim).reset()
    pfwp = pfwp.vertices().fillet(pf_fillets).clean().reset()
    # swp = swp.wires().offset(gland_width / 2 + min_wall).clean().reset()  # edge of passthrough part
    # + screw_nominal_d + (screw_head_nominal_d / 2 - screw_nominal_d / 2) + min_wall
    passthrough_face = pfwp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the passthrough part

    pfwp = pfwp.wires().offset(min_gap).clean().reset()  # edge of recess_cut
    recess_face = pfwp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the recess

    # fastening screw hole points
    fhps = []
    fhps.append(((board_width - 2 * block_width / 2) / 2, pcbt / 2 + ffo + min_wall + gland_width + min_wall + fix_scr.clearance_hole_diameters["Close"] / 2))
    fhps.append((-(board_width - 2 * block_width / 2) / 2, pcbt / 2 + ffo + min_wall + gland_width + min_wall + fix_scr.clearance_hole_diameters["Close"] / 2))
    fhps.append((bcx, pcbt / 2 + ffo - co_tw - min_wall - gland_width - min_wall - fix_scr.clearance_hole_diameters["Close"] / 2))
    fhps.append((-bcx, pcbt / 2 + ffo - co_tw - min_wall - gland_width - min_wall - fix_scr.clearance_hole_diameters["Close"] / 2))

    def _make_pcb(what):
        """build the actual passthrough PCB"""
        # this copies some logic in the eachpoint() function so that we can use each() which is safer
        base_plane = self.plane
        base = base_plane.location
        if isinstance(what, (cq.Vector, cq.Shape)):
            loc = base.inverse * cq.Location(base_plane, what.Center())
        elif isinstance(what, cq.Sketch):
            loc = base.inverse * cq.Location(base_plane, what._faces.Center())
        else:
            loc = what

        pcb = CQ().workplane(offset=-wall_depth - board_inner_depth)
        pcb = pcb.rect(board_width, pcbt).extrude(until=board_inner_depth + wall_depth + board_outer_depth)

        pcb = pcb.edges("|Y").fillet(pcb_corner)

        # put in screws with holes
        hardware = cadquery.Assembly()
        pcb = pcb.faces(">Y").workplane(**u.cobb).rarray(board_width - 2 * block_width / 2, board_inner_depth + board_outer_depth + wall_depth - 2 * pt_pcb_mount_hole_offset[0], 2, 2).clearanceHole(pcb_scr, fit="Close", counterSunk=False, baseAssembly=hardware)
        if hw_asy is not None:
            hw_asy.add(hardware, loc=base * loc)

        # put in pin0 holes
        pcb = pcb.faces(">Y").workplane(**u.copo, origin=(0, 0, 0)).pushPoints(p0pts).circle(pin0_holed / 2).cutThruAll()

        return pcb.findSolid().moved(base * loc)

    def _make_pt(what):
        """build a passthrough component"""
        # this copies some logic in the eachpoint() function so that we can use each() which is safer
        base_plane = self.plane
        base = base_plane.location
        if isinstance(what, (cq.Vector, cq.Shape)):
            loc = base.inverse * cq.Location(base_plane, what.Center())
        elif isinstance(what, cq.Sketch):
            loc = base.inverse * cq.Location(base_plane, what._faces.Center())
        else:
            loc = what

        hardware = cadquery.Assembly()
        passthrough = CQ().add(passthrough_face)
        passthrough = passthrough.wires().toPending().extrude(-part_thickness)  # extrude the bulk
        slotd = pcbt + 2 * min_gap
        passthrough = passthrough.workplane(centerOption="ProjectedOrigin").slot2D(length=board_width + slotd / 2, diameter=slotd, angle=0).cutThruAll()  # cut the pcb slot
        # TODO: retool some geometry because this cutout could possibly interfere with the oring gland for thick PCBs

        # cut the oring groove
        cq.Workplane.mk_groove = groovy.mk_groove
        oring_path = o_face.outerWire().translate((0, 0, -part_thickness))
        passthrough = passthrough.faces("<<Z").workplane(**u.copo).add(oring_path).toPending().mk_groove(ring_cs=oring_cs, hardware=hardware)

        # cut the fastening screw holes
        passthrough = passthrough.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).pushPoints(fhps).clearanceHole(fix_scr, fit="Close", baseAssembly=hardware)

        # add the support towers
        in_post_length = wall_depth + board_inner_depth
        passthrough = passthrough.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).sketch().push(sbpts).rect(*support_block).finalize().extrude(-in_post_length)
        passthrough = passthrough.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).sketch().push(sbpts).rect(*support_block).finalize().extrude(board_outer_depth)
        # mount holes
        pcb_center_z = ((board_outer_depth) - (wall_depth + board_inner_depth)) / 2
        passthrough = passthrough.faces("+Y").faces(">>Z").workplane(**u.copo, origin=(0, 0, pcb_center_z)).rarray(board_width - 2 * pt_pcb_mount_hole_offset[1], board_inner_depth + board_outer_depth + wall_depth - 2 * pt_pcb_mount_hole_offset[0], 2, 2).clearanceHole(pcb_scr, fit="Close", counterSunk=False)
        passthrough = passthrough.edges("<<Z or >>Z").edges("|Y").fillet(pcb_corner)
        passthrough = passthrough.edges("<<Z[-1] or <<Z[-2] or <<Z[-3] or >>Z[-1] or >>Z[-2] or >>Z[-3]").chamfer(0.5)

        if hw_asy is not None:
            hw_asy.add(hardware, loc=base * loc)

        return passthrough.findSolid().moved(base * loc)

    def _make_neg(what):
        """makes a negative shape to be cut out of the parent walls"""
        # this copies some logic in the eachpoint() function so that we can use each() which is safer
        base_plane = self.plane
        base = base_plane.location
        if isinstance(what, (cq.Vector, cq.Shape)):
            loc = base.inverse * cq.Location(base_plane, what.Center())
        elif isinstance(what, cq.Sketch):
            loc = base.inverse * cq.Location(base_plane, what._faces.Center())
        else:
            loc = what

        # fastener threaded holes
        # TODO: mark these holes as "M3-0.5 threaded" in the engineering drawing
        fhs = CQ().pushPoints(fhps).circle(fix_scr.tap_hole_diameters["Soft"] / 2).extrude(-wall_depth + pt_fix_wall_buffer)

        nwp = CQ().add(through_face)
        through = nwp.wires().toPending().extrude(-wall_depth)

        nwp2 = CQ().add(recess_face)
        recess = nwp2.wires().toPending().extrude(-part_thickness)

        neg = recess.union(through).union(fhs)

        return neg.findSolid().moved(base * loc)

    rslt = self.each(_make_neg, useLocalCoordinates=False, combine="cut", clean=True)

    # pass out the passthrough geometry
    if pt_asy is not None:
        passthroughs = self.each(_make_pt, useLocalCoordinates=False, combine=False).vals()
        for i, passthrough in enumerate(passthroughs):
            pt_asy.add(passthrough.Solids()[0], name=f"passthrough {i}")

    # pass out the pcb geometry
    if pcb_asy is not None:
        # pcbs = self.eachpoint(lambda loc: _make_pcb().moved(loc), useLocalCoordinates=True, combine=False).vals()
        pcbs = self.each(_make_pcb, useLocalCoordinates=False, combine=False).vals()
        for i, pcb in enumerate(pcbs):
            pcb_asy.add(pcb.Solids()[0], name=f"pcb {i}")

    return rslt


def make_cut(self, rows=8, angle=0, kind="C", mfg="samtec"):
    global surface_length
    if mfg == "samtec":
        connector_height = 8.78 + 0.15  # mm SAMTEC MECF-XX-01-L-DV-NP-WT (worst case (largest) size)
        connector_width = 5.6 + 0.13  # mm SAMTEC MECF-XX-01-L-DV-NP-WT (worst case (largest) size)
        if rows == 8:
            con_len = 18.34 + 0.13
            pcb_len = 11.91
        elif rows == 20:
            con_len = 33.58 + 0.13
            pcb_len = 27.15
        else:
            raise (ValueError("Only 8 or 20 row connectors are supported"))
    else:
        raise (ValueError("Manufacturer not supported"))

    gp_buffer = 2  # space around the card edge for the glue pocket
    pcb_clearance = 0.1  # space around the card edge
    gp_depth = 1.5  # depth of the sealant glue pocket
    min_gp_connector_pocket_spacing = 1  # smallest wall thickness between the glue pocket and the connector pocket
    chamfer_length = 1.5  # length of the connector guiding chamfers
    con_clearance = 0.10  # clearance around the connector in its pocket
    r = 1.5  # assumed radius of the cutting tool for cutting the pocket

    surface_length = con_len + 2 * chamfer_length

    test_hole_length = self.largestDimension()

    def _makeNegative(center):
        """
        Generates the pocket shape we'll be cutting out
        """

        # the connector pocket's dimensions
        pocket_w = connector_width + con_clearance * 2
        pocket_l = con_len + con_clearance * 2
        pocket_d = connector_height + con_clearance

        # find the source thing's thickness at the cut point
        swiss = CQ(self.plane).add(self.findSolid())
        cheese = CQ(self.plane).add(self.findSolid()).pushPoints([center]).circle(0.5).cutThruAll()
        core = swiss.cut(cheese)
        this_thikness = u.find_length(core, along="normal", bb_method=False)

        min_thickness = pocket_d + min_gp_connector_pocket_spacing + gp_depth

        # check that it's thick enough here
        if this_thikness < min_thickness:
            raise (ValueError(f"The part is too thin (thickness = {this_thikness}) at {center} to cut the PCB pocket"))

        # make a box to subtract from
        start_box = CQ("XY").box(100, 100, this_thikness, centered=(True, True, False))

        # make a simple pocket that we'll use for the chamfer operation
        result = start_box.faces("<Z").rect(pocket_w, pocket_l).cutBlind(pocket_d)

        # chamfer the connector edge
        result = result.faces("<Z").edges("not(<X or >X or <Y or >Y)").chamfer(chamfer_length)

        # now make the undercut pocket
        CQ.undercutRelief2D = u.undercutRelief2D
        result = result.faces("<Z").workplane().undercutRelief2D(pocket_l, pocket_w, diameter=r * 2, angle=90, kind=kind).cutBlind(pocket_d)

        # cut out the glue pocket
        slot_width = c.pcb_thickness + 2 * gp_buffer
        slot_len = pcb_len + slot_width
        result = result.faces(">Z").workplane().slot2D(slot_len, slot_width, angle=90).cutBlind(-gp_depth)

        # cut out the pcb passthrough slot
        slot_width = c.pcb_thickness + 2 * pcb_clearance
        slot_len = pcb_len + slot_width
        result = result.faces(">Z").workplane().slot2D(slot_len, slot_width, angle=90).cutThruAll()

        # invert the geometry and rotate the negative
        negative = start_box.cut(result)
        negative = negative.rotate((0, 0, 0), (0, 0, 1), angle)
        to_cut = negative.findSolid().locate(center)
        to_cut = to_cut.mirror("XY")
        return to_cut

    rslt = self.cutEach(_makeNegative, useLocalCoords=True, clean=True)
    return rslt
