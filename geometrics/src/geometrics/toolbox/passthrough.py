import cadquery as cq
from . import utilities as u
from . import constants as c

"""
cuts a pcb card edge passthrough through something
along the Z direction
"""

# length of the connector passthrough geometry on the bottom surface
surface_length: float = None  # type: ignore[assignment]


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
            raise(ValueError("Only 8 or 20 row connectors are supported"))
    else:
        raise(ValueError("Manufacturer not supported"))

    gp_buffer = 2  # space around the card edge for the glue pocket
    pcb_clearance = 0.1  # space around the card edge
    gp_depth = 1.5  # depth of the sealant glue pocket
    min_gp_connector_pocket_spacing = 1  # smallest wall thickness between the glue pocket and the connector pocket
    chamfer_length = 1.5  # length of the connector guiding chamfers
    con_clearance = 0.10  # clearance around the connector in its pocket
    r = 1.5  # assumed radius of the cutting tool for cutting the pocket

    surface_length = con_len + 2*chamfer_length

    test_hole_length = self.largestDimension()

    def _makeNegative(center):
        """
        Generates the pocket shape we'll be cutting out
        """

        # the connector pocket's dimensions
        pocket_w = connector_width+con_clearance*2
        pocket_l = con_len+con_clearance*2
        pocket_d = connector_height + con_clearance

        # find the source thing's thickness at the cut point
        # TODO: check that this works when cutting into objects from a non-"<Z" face
        swiss = self.copyWorkplane(self)
        cheese = self.copyWorkplane(self).pushPoints([center]).circle(0.5).cutThruAll()
        core = swiss.cut(cheese)
        this_thikness = u.find_length(core, along="Z", bb_method=True)

        min_thickness = pocket_d + min_gp_connector_pocket_spacing + gp_depth

        # check that it's thick enough here
        if this_thikness < min_thickness:
            raise(ValueError(f"The part is too thin (thickness = {this_thikness}) at {center} to cut the PCB pocket"))

        # make a box to subtract from
        start_box = cq.Workplane("XY").box(100, 100, this_thikness, centered=(True, True, False))

        # make a simple pocket that we'll use for the chamfer operaion
        result = start_box.faces("<Z").rect(pocket_w, pocket_l).cutBlind(pocket_d)

        # chamfer the connector edge
        result = result.faces("<Z").edges("not(<X or >X or <Y or >Y)").chamfer(chamfer_length)

        # now make the undercut pocket
        cq.Workplane.undercutRelief2D = u.undercutRelief2D
        result = result.faces("<Z").undercutRelief2D(pocket_l, pocket_w, diameter=r*2, angle=90, kind=kind).cutBlind(pocket_d)

        # cut out the glue pocket
        slot_width = c.pcb_thickness+2*gp_buffer
        slot_len = pcb_len+slot_width
        result = result.faces(">Z").slot2D(slot_len, slot_width, angle=90).cutBlind(-gp_depth)

        # cut out the pcb passthrough slot
        slot_width = c.pcb_thickness+2*pcb_clearance
        slot_len = pcb_len+slot_width
        result = result.faces(">Z").slot2D(slot_len, slot_width, angle=90).cutThruAll()

        # invert the geometry and rotate the negative
        negative = start_box.cut(result)
        negative = negative.rotate((0, 0, 0), (0, 0, 1), angle)
        to_cut = negative.findSolid().locate(center)
        to_cut = to_cut.mirror("XY")
        return to_cut
    rslt = self.cutEach(_makeNegative, useLocalCoords=True, clean=True)
    return rslt


if "show_object" in locals():
    cq.Workplane.passthrough = make_cut
    mwp = cq.Workplane("front").circle(80.0).extrude(20)
    mwp = mwp.translate((99,99,99))
    mwp = mwp.faces(">Z").workplane(centerOption='CenterOfBoundBox')
    mwp = mwp.rarray(30, 20, 2, 2).passthrough(rows=8, angle=80, kind="C")
