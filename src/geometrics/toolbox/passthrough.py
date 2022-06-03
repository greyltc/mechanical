import math
from re import S
from cadquery import cq, CQ
import cadquery
from . import utilities as u
from . import constants as c
from . import groovy
import logging
from cq_warehouse.fastener import CounterSunkScrew, ButtonHeadScrew, CheeseHeadWasher
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
    board_width: float = 82.7,
    board_inner_depth: float = 9.27,
    board_outer_depth: float = 9.27,
    part_thickness: float = 0,
    wall_depth: float = 0,
    screw="M3-0.5",
    pt_asy: cadquery.Assembly = None,
    pcb_asy: cadquery.Assembly = None,
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

    block_width = 6
    block_height_nominal = 6
    support_block = (block_width, block_height_nominal - washert)  # actual support block (leaves room for washer)
    c_block = (block_width, block_height_nominal)  # virtual support block (includes washer)
    c_block2 = (block_width, block_height_nominal + pcbt)  # virtual support block2 (includes parts of PCB)

    pcb_corner = 2
    pt_pcb_mount_hole_offset = (4.445, block_width / 2)  # from corners

    fix_scr = CounterSunkScrew(size=screw, fastener_type="iso14581", length=wall_depth * 0.8)
    pcb_scr = ButtonHeadScrew(size=screw, fastener_type="iso7380_1", length=block_height_nominal + 3)
    # washer = CheeseHeadWasher(size=screw, fastener_type="iso7092")

    oring_cs = 1  # oring thickness

    min_radius = oring_cs * 3  # min inner bend radius
    min_wall = 0.8  # walls should not be mfg'd thinner than this

    min_gap = 0.25  # cutting tolerances prevent smaller gaps between things

    gland_width = groovy.get_gland_width(oring_cs)
    effective_gland_width = (round(gland_width * 100) + 1) / 100  # rounded up to the nearest 0.01mm
    logger.info(f"Using {effective_gland_width=}")

    # some important radii for construction to ensure we don't overbend the o-ring
    minr1 = min_radius - min_wall
    minr2 = min_radius + min_wall + effective_gland_width

    # virtual support block centers
    sby = -pcbt / 2 - c_block[1] / 2
    sbx = board_width / 2 - support_block[0] / 2
    vbpts = []
    vbpts.append((-sbx, sby))
    vbpts.append((sbx, sby))
    vb2pts = [(p[0], p[1] + pcbt / 2) for p in vbpts]

    # actual support block centers
    sbpts = [(p[0], p[1] - washert / 2) for p in vbpts]

    # make the through cutout
    in_off = minr1 - min_gap - (minr1 - min_gap) * 2**0.5 / 2  # exact inward offset to get min_gap spacing with minr1 fillets
    in_off_eff = (round(in_off * 100) + 1) / 100  # effective inward offset to make numbers round to 0.01mm
    ffo = in_off_eff + min_gap  # clearance between through parts flats and the flats of the cutout
    co_tw = minr1 * 2 + min_gap  # width of the thin part of the cutout (so that the cutting tool can easily fit)
    twl = board_width - 2 * ffo - 2 * support_block[0]  # length of the thin part
    twh = c_block[1] + 2 * ffo + pcbt - co_tw  # height of the negative
    twr = (twl, twh)  # thin with negative rect dims
    twx = 0  # thin width cutout center y
    twy = twh / 2 - pcbt / 2 - c_block[1] - ffo  # thin width cutout center y
    twc = (twx, twy)  # thin width cutout center
    o = co_tw + minr2 - (ffo + pcbt + c_block[1] + ffo - minr1)  # opposite
    h = minr2 + minr1  # hypotenuse
    a = o / math.tan(math.asin(o / h))  # adjacent
    bcx = board_width / 2 - support_block[0] - a + minr1 - ffo  # big circle x
    bcy = pcbt / 2 + ffo - (co_tw + minr2)
    bcpts = []
    bcpts.append((-bcx, bcy))
    bcpts.append((bcx, bcy))

    c_block3 = [p + 2 * ffo for p in c_block2]  # expanded with clearance
    vb3pts = vb2pts

    c_block4 = [board_width + 2 * ffo, 2 * ffo + pcbt + washert + support_block[1]]  # one construction block spanning across
    vb4pts = (0, -c_block4[1] / 2 + pcbt / 2 + ffo)

    swp = CQ().sketch()  # make sketch workplane
    swp = swp.push([vb4pts]).rect(*c_block4).reset()
    swp = swp.push(bcpts).circle(minr2, mode="s").clean().reset()  # cut away the large circles
    swp = swp.push([(0, bcy)]).rect(2 * bcx, minr2 * 2, mode="s").clean().reset()  # cut away the space between the circles
    swp = swp.vertices().fillet(minr1).clean().reset()  # round all the remaining edges
    through_face = swp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the through cut

    swp = swp.wires().offset(min_wall + effective_gland_width / 2).clean().reset()  # inner edge of ogland
    o_face = swp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the oring path wire

    # passthrough face
    pfw = min_wall + effective_gland_width + min_wall + c_block4[0] + min_wall + effective_gland_width + min_wall  # passthrough face width
    pfha = min_wall + effective_gland_width + min_wall + screw_nominal_d + (screw_head_nominal_d / 2 - screw_nominal_d / 2) + min_wall  # passthrough face height above cutout top edge
    pfhb1 = co_tw + min_wall + effective_gland_width + min_wall + screw_nominal_d + (screw_head_nominal_d / 2 - screw_nominal_d / 2) + min_wall  # passthrough face height below cutout top edge
    pfhb2 = ffo + pcbt + block_height_nominal + ffo + min_wall + effective_gland_width + min_wall  # passthrough face height below cutout top edge if limited by support block clearance
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
    # swp = swp.wires().offset(effective_gland_width / 2 + min_wall).clean().reset()  # edge of passthrough part
    # + screw_nominal_d + (screw_head_nominal_d / 2 - screw_nominal_d / 2) + min_wall
    passthrough_face = pfwp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the passthrough part

    pfwp = pfwp.wires().offset(min_gap).clean().reset()  # edge of recess_cut
    recess_face = pfwp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the recess

    def _make_pcb(loc):
        """build the actual passthrough PCB"""
        pcb = CQ().workplane(offset=-wall_depth - board_inner_depth)
        pcb = pcb.rect(board_width, pcbt).extrude(until=board_inner_depth + wall_depth + board_outer_depth)

        pcb = pcb.edges("|Y").fillet(pcb_corner)
        pcb = pcb.faces(">Y").workplane(**u.cobb).rarray(board_width - 2 * block_width / 2, board_inner_depth + board_outer_depth + wall_depth - 2 * pt_pcb_mount_hole_offset[0], 2, 2).clearanceHole(pcb_scr, fit="Close", counterSunk=False)

        return pcb.findSolid().moved(loc)

    def _make_pt(loc):
        """build a passthrough component"""
        passthrough = CQ().add(passthrough_face)
        passthrough = passthrough.wires().toPending().extrude(-part_thickness)  # extrude the bulk
        slotd = pcbt + 2 * min_gap
        passthrough = passthrough.workplane(centerOption="ProjectedOrigin").slot2D(length=board_width + slotd / 2, diameter=slotd, angle=0).cutThruAll()  # cut the pcb slot
        # TODO: retool some geometry because this cutout could possibly interfere with the oring gland for thick PCBs

        # cut the oring groove
        cq.Workplane.mk_groove = groovy.mk_groove
        oring_path = o_face.outerWire().translate((0, 0, -part_thickness))
        passthrough = passthrough.faces("<<Z").workplane(**u.copo).add(oring_path).toPending().mk_groove(ring_cs=oring_cs)

        # cut the fastening screw holes
        passthrough = passthrough.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).center(0, pcbt / 2 + ffo + min_wall + effective_gland_width + min_wall + fix_scr.clearance_hole_diameters["Close"] / 2).rarray(board_width - 2 * block_width / 2, 1, 2, 1).clearanceHole(fix_scr, fit="Close")
        passthrough = passthrough.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).center(0, pcbt / 2 + ffo - co_tw - min_wall - effective_gland_width - min_wall - fix_scr.clearance_hole_diameters["Close"] / 2).rarray(2 * bcx, 1, 2, 1).clearanceHole(fix_scr, fit="Close")

        # add the support towers
        in_post_length = wall_depth + board_inner_depth
        passthrough = passthrough.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).sketch().push(sbpts).rect(*support_block).finalize().extrude(-in_post_length)
        passthrough = passthrough.faces(">Z").workplane(**u.copo, origin=(0, 0, 0)).sketch().push(sbpts).rect(*support_block).finalize().extrude(board_outer_depth)
        # mount holes
        # passthrough = passthrough.faces("+Y").faces(">>Z or <<Z").workplane(**u.cobo).rarray(board_width - 2 * pt_pcb_mount_hole_offset[1], board_inner_depth + board_outer_depth + wall_depth - 2 * pt_pcb_mount_hole_offset[0], 2, 2).clearanceHole(pcb_scr, fit="Close", counterSunk=False)
        passthrough = passthrough.faces("+Y").faces(">>Z").faces(">>X").workplane(**u.cobb).center(0, board_outer_depth / 2 - pt_pcb_mount_hole_offset[0]).clearanceHole(pcb_scr, fit="Close", counterSunk=False)
        passthrough = passthrough.faces("+Y").faces(">>Z").faces("<<X").workplane(**u.cobb).center(0, board_outer_depth / 2 - pt_pcb_mount_hole_offset[0]).clearanceHole(pcb_scr, fit="Close", counterSunk=False)
        passthrough = passthrough.faces("+Y").faces("<<Z").faces("<<X").workplane(**u.cobb).center(0, -(in_post_length - part_thickness) / 2 + pt_pcb_mount_hole_offset[0]).clearanceHole(pcb_scr, fit="Close", counterSunk=False)
        passthrough = passthrough.faces("+Y").faces("<<Z").faces(">>X").workplane(**u.cobb).center(0, -(in_post_length - part_thickness) / 2 + pt_pcb_mount_hole_offset[0]).clearanceHole(pcb_scr, fit="Close", counterSunk=False)
        passthrough = passthrough.edges("<<Z or >>Z").edges("|Y").fillet(pcb_corner)
        passthrough = passthrough.edges("<<Z[-1] or <<Z[-2] or <<Z[-3] or >>Z[-1] or >>Z[-2] or >>Z[-3]").chamfer(0.5)

        return passthrough.findSolid().moved(loc)

    def _make_neg(loc):
        """makes a negative shape to be cut out of the parent"""
        nwp = CQ().add(through_face)
        through = nwp.wires().toPending().extrude(-wall_depth)

        nwp2 = CQ().add(recess_face)
        recess = nwp2.wires().toPending().extrude(-part_thickness)

        neg = recess.union(through)

        return neg.findSolid().moved(loc)

    rslt = self.eachpoint(_make_neg, useLocalCoordinates=True, combine="cut", clean=True)

    # pass out the passthrough geometry
    if pt_asy is not None:
        passthroughs = self.eachpoint(_make_pt, useLocalCoordinates=True, combine=False).vals()
        for i, passthrough in enumerate(passthroughs):
            pt_asy.add(passthrough.Solids()[0], name=f"passthrough {i}")

    # pass out the pcb geometry
    if pcb_asy is not None:
        # pcbs = self.eachpoint(lambda loc: _make_pcb().moved(loc), useLocalCoordinates=True, combine=False).vals()
        pcbs = self.eachpoint(_make_pcb, useLocalCoordinates=True, combine=False).vals()
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
