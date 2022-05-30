import math
from re import S
from cadquery import cq, CQ
from . import utilities as u
from . import constants as c
from . import groovy

"""
cuts a pcb card edge passthrough through something
along the Z direction
"""

# length of the connector passthrough geometry on the bottom surface
surface_length: float = None  # type: ignore[assignment]


def make_oringer(self, board_width=82.7, board_inner_depth=9.27, board_outer_depth=9.27, wall_depth=None):
    if wall_depth is None:  # if depth is not given do our best to find it
        wall_depth = u.find_length(self, along="normal", bb_method=False)

    pcbt = 1.6  # pcb thickness
    washert = 0.5  # washer thickness

    c_block = (6, 6)  # virtual support block (includes washer)
    c_block2 = (6, 6 + pcbt)  # virtual support block2 (includes parts of PCB)
    support_block = (c_block[0], c_block[1] - washert)  # actual support block (leaves room for washer)

    oring_cs = 1  # oring thickness

    min_radius = oring_cs * 3  # min inner bend radius
    min_wall = 0.8  # walls should not be mfg'd thinner than this

    min_gap = 0.25  # cutting tolerances prevent smaller gaps between things

    gland_width = groovy.get_gland_width(oring_cs)
    effective_gland_width = (round(gland_width * 100) + 1) / 100  # rounded up to the nearest 0.01mm

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
    through_face = swp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the cut

    swp = swp.wires().offset(min_wall + effective_gland_width / 2).clean().reset()  # inner edge of ogland
    o_face = swp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the oring path wire

    swp = swp.wires().offset(min_wall + effective_gland_width / 2 + min_gap).clean().reset()  # edge of recess_cut
    recess_face = swp.finalize().extrude(-1).faces(">>Z").val()  # get just the face for the recess

    def _make_neg():
        """makes a negative shape to be cut out of the parent"""
        nwp = CQ().add(through_face)
        through = nwp.wires().toPending().extrude(-wall_depth)

        nwp2 = CQ().add(recess_face)
        recess = nwp2.wires().toPending().extrude(-wall_depth / 2)

        neg = recess.union(through)

        return neg.findSolid()

    rslt = self.eachpoint(lambda loc: _make_neg().moved(loc), useLocalCoordinates=True, combine="cut", clean=True)
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
