import cadquery as cq
import toolbox as tb

"""
cuts a pcb card edge passthrough through something
along the Z direction
"""


def make_cut(source, rows=8, clean=True):
    connector_height = 8.78 + 0.15  # mm SAMTEC MECF-XX-01-L-DV-NP-WT (worst case (largest) size)
    connector_width = 5.6 + 0.13  # mm SAMTEC MECF-XX-01-L-DV-NP-WT (worst case (largest) size)

    gp_buffer = 2  # space around the card edge for the glue pocket
    pcb_clearance = 0.1 # space around the card edge
    gp_depth = 1.5  # depth of the sealant glue pocket
    min_gp_connector_pocket_spacing = 1  # smallest wall thickness between the glue pocket and the connector pocket
    chamfer_length = 1.5 # length of the connector guiding chamfers
    con_clearance = 0.10 # clearance around the connector in its pocket
    r = 1.5 # assumed radius of the cutting tool for cutting the pocket

    p_depth = 5
    plen = 20
    pwid = 4

    if rows == 8:
        con_len = 18.34 + 0.13
        pcb_len = 11.91
    elif rows == 20:
        con_len = 33.58 + 0.13
        pcb_len = 27.15
    else:
        raise(ValueError("Only 8 or 20 row connectors are supported"))

    def _makeNegative(source_thing, center):
        """
        Generates the pocket shape we'll be cutting out
        """

        # the connector pocket's dimensions
        pocket_w = connector_width+con_clearance*2
        pocket_l = con_len+con_clearance*2
        pocket_d = connector_height + con_clearance

        # find the source thing's thickness at the cut point
        boreDir = Vector(0, 0, -1)
        test_hole = cq.Solid.makeCylinder(0.5, source_thing.largestDimension(), center, boreDir)  # local coordianates!
        this_thikness = tb.u.find_length(source_thing.intersect(test_hole), along="Z")

        min_thickness = pocket_d + min_gp_connector_pocket_spacing + gp_depth

        if this_thikness < min_thickness:
            raise(ValueError(f"The part is too thin at {center} to cut the PCB pocket"))

        # make a box to subtract from
        start_box = cq.Workplane("front").box(100, 100, this_thikness)

        result = start_box.faces("<Z").rect(pocket_w, pocket_l).cutBlind(pocket_d)

        # chamfer the connector edge
        result = result.faces("<Z").edges("not(<X or >X or <Y or >Y)").chamfer(chamfer_length)

        # cut out the glue pocket
        result = result.faces(">Z").slot2D(pcb_len, tb.c.pcb_thickness+2*gp_buffer, 90).cutBlind(-gp_depth)

        # cut out the pcb passthrough slot
        result = result.faces(">Z").slot2D(pcb_len+2*pcb_clearance, tb.c.pcb_thickness+2*pcb_clearance, 90).cutThruAll()

        # invert the geometry
        negative = start_box.cut(result)

        return negative.translate((center[0, center[1], 0]))

    return source.cutEach(_makeNegative, True, clean)
