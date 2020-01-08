import cadquery as cq
import toolbox as tb

"""
cuts a pcb card edge passthrough through something
along the Z direction
"""

# length of the connector passthrough geometry on the bottom surface
surface_length: float = None  # type: ignore[assignment]

def make_cut(self, rows=8, angle=0, clean=True, kind="C"):
    global surface_length
    connector_height = 8.78 + 0.15  # mm SAMTEC MECF-XX-01-L-DV-NP-WT (worst case (largest) size)
    connector_width = 5.6 + 0.13  # mm SAMTEC MECF-XX-01-L-DV-NP-WT (worst case (largest) size)

    gp_buffer = 2  # space around the card edge for the glue pocket
    pcb_clearance = 0.1  # space around the card edge
    gp_depth = 1.5  # depth of the sealant glue pocket
    min_gp_connector_pocket_spacing = 1  # smallest wall thickness between the glue pocket and the connector pocket
    chamfer_length = 1.5  # length of the connector guiding chamfers
    con_clearance = 0.10  # clearance around the connector in its pocket
    r = 1.5  # assumed radius of the cutting tool for cutting the pocket

    if rows == 8:
        con_len = 18.34 + 0.13
        pcb_len = 11.91
    elif rows == 20:
        con_len = 33.58 + 0.13
        pcb_len = 27.15
    else:
        raise(ValueError("Only 8 or 20 row connectors are supported"))

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
        boreDir = cq.Vector(0, 0, 1)
        test_hole = cq.Solid.makeCylinder(0.5, test_hole_length, center, boreDir).translate((0, 0, -test_hole_length/2))
        intersection = self.intersect(test_hole)
        this_thikness = tb.u.find_length(intersection, along="Z")

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
        cq.Workplane.undercutRelief2D = tb.u.undercutRelief2D
        result = result.faces("<Z").undercutRelief2D(pocket_l, pocket_w, diameter=r*2, angle=90, kind=kind).cutBlind(pocket_d)

        # cut out the glue pocket
        slot_width = tb.c.pcb_thickness+2*gp_buffer
        slot_len = pcb_len+slot_width
        result = result.faces(">Z").slot2D(slot_len, slot_width, angle=90).cutBlind(-gp_depth)

        # cut out the pcb passthrough slot
        slot_width = tb.c.pcb_thickness+2*pcb_clearance
        slot_len = pcb_len+slot_width
        result = result.faces(">Z").slot2D(slot_len, slot_width, angle=90).cutThruAll()

        # invert the geometry and rotate the negative
        negative = start_box.cut(result)
        negative = negative.rotate((0, 0, 0), (0, 0, 1), angle)

        return negative.findSolid().translate(center)

    return self.cutEach(_makeNegative, False, clean)
