import cadquery as cq
import toolbox as tb

"""
block for mounting PCBs
"""

width: float = None  # type: ignore[assignment]
length: float = None  # type: ignore[assignment]
height: float = None  # type: ignore[assignment]
csk_diameter: float = None  # type: ignore[assignment]
base_mount_screw_size: float = None  # type: ignore[assignment]

# these two numbers are taken from the PCB design
pcb_mount_hole_bottom_height = 3.5
pcb_mount_hole_spacing = 13

chamfer_l = 0.5

aux_hole_spacing = 16
alignment_updent_diameter_nominal = 3
alignment_updent_diameter = alignment_updent_diameter_nominal - 0.05
alignment_updent_height = 1
alignment_updent_chamfer = 0.25

# this number allows these holes to be vents for the pf dowels
back_aux_hole_from_top = 11

pressfit_hole_diameter_nominal = 3
pressfit_hole_diameter = pressfit_hole_diameter_nominal - 0.035
pressfit_hole_depth = 10

blind_hole_depth = 7.5
pcb_mount_hole_x_center_from_edge = 3

def build(
    adapter_width=30,
    block_length=12,
    block_height=19.5,
    special_chamfer=0,  # for giving clearance for otter's alignment pin
    vertm3s=False,
    horzm3s=False,
    align_bumps=False,
    pfdowel=False,
    thread_length_from_bottom=0,  # if non-zero, instead of a countersink from above, we'll get this many mm of threads up from the bottom
    base_mount_screw="m5", 
):
    """
    Builds up an endblock.
    vertm3s True means there will be two m3 csk holes vertically up from the bottom
    spaced by top_hole_spacing
    horzm3s means there will two m3 mounts on the back
    align_bumps means there will be two updents in the top
    pfdowel means there will be holes for pressfit dowels in the top

    """
    global width, length, height, csk_diameter, base_mount_screw_size
    cska = tb.c.std_countersinks[base_mount_screw]["angle"]

    if (vertm3s is True) and (horzm3s is True):
        raise (ValueError("Hole collision while building endblock"))

    if sum((pfdowel, align_bumps, vertm3s)) > 1:
        raise (ValueError("Only one can be true: vertm3s, align_bumps, pfdowel"))

    width = adapter_width - tb.c.pcb_thickness
    length = block_length
    height = block_height
    base_mount_screw_size = base_mount_screw

    pcb_mount_holea_z = -block_height / 2 + pcb_mount_hole_bottom_height
    pcb_mount_holeb_z = pcb_mount_holea_z + pcb_mount_hole_spacing

    pcb_mount_hole_x = length / 2 - pcb_mount_hole_x_center_from_edge

    back_aux_hole_z = block_height / 2 - back_aux_hole_from_top

    # build the block
    block = cq.Workplane("XY").box(length, width, height)

    # put in the PCB mounting holes
    cskbd = tb.c.std_screw_threads["m2"]["tap_r"] * 2
    block = (
        block.faces(">Y")
        .workplane(centerOption="CenterOfBoundBox")
        .center(pcb_mount_hole_x, pcb_mount_holea_z)
        .cskHole(
            cskbd,
            cskDiameter=cskbd + 2 * chamfer_l,
            depth=blind_hole_depth,
            cskAngle=cska,
        )
    )
    block = (
        block.faces(">Y")
        .workplane(centerOption="CenterOfBoundBox")
        .center(pcb_mount_hole_x, pcb_mount_holeb_z)
        .cskHole(
            cskbd,
            cskDiameter=cskbd + 2 * chamfer_l,
            depth=blind_hole_depth,
            cskAngle=cska,
        )
    )
    block = (
        block.faces("<Y")
        .workplane(centerOption="CenterOfBoundBox")
        .center(-pcb_mount_hole_x, pcb_mount_holea_z)
        .cskHole(
            cskbd,
            cskDiameter=cskbd + 2 * chamfer_l,
            depth=blind_hole_depth,
            cskAngle=cska,
        )
    )
    block = (
        block.faces("<Y")
        .workplane(centerOption="CenterOfBoundBox")
        .center(-pcb_mount_hole_x, pcb_mount_holeb_z)
        .cskHole(
            cskbd,
            cskDiameter=cskbd + 2 * chamfer_l,
            depth=blind_hole_depth,
            cskAngle=cska,
        )
    )
        
    block = block.faces("<Z").edges("%Line").chamfer(chamfer_l)
    if special_chamfer == 0:
        special_chamfer = chamfer_l
    special_chamfer_diff = special_chamfer - chamfer_l
    block = block.faces(">Z").edges("|X").chamfer(chamfer_l)
    block = block.faces(">Z").edges("<X").chamfer(special_chamfer)
    block = block.faces(">Z").edges(">X").chamfer(chamfer_l)
    block = block.edges("|Z and %Line").chamfer(chamfer_l)

    if thread_length_from_bottom == 0:
        csk_diameter = length - 1.5

        # base mount hole for use with RS Stock No. 908-7532 machine screws
        csktd = 2 * tb.c.std_screw_threads[base_mount_screw_size]["close_r"]
        block = (
            block.faces(">Z")
            .workplane(centerOption="CenterOfBoundBox").center(-special_chamfer_diff/2, 0)
            .cskHole(csktd, cskDiameter=csk_diameter, cskAngle=cska)
        )
        # chamfer the exit hole
        block = (
            block.faces("<Z")
            .workplane(centerOption="CenterOfBoundBox")
            .cskHole(csktd, cskDiameter=csktd + 2 * chamfer_l, cskAngle=cska)
        )
    else:
        block = (
            block.faces("<Z")
            .workplane(centerOption="CenterOfBoundBox")
            .circle(2 * tb.c.std_screw_threads[base_mount_screw_size]["tap_r"])
            .cutBlind(thread_length_from_bottom)
        )


    # 2x threaded countersunk holes on the back side
    if horzm3s is True:
        cskbd = 2 * tb.c.std_screw_threads["m3"]["tap_r"]
        dm3pts = [
            (-aux_hole_spacing / 2, back_aux_hole_z),
            (aux_hole_spacing / 2, back_aux_hole_z),
        ]
        back_face = block.faces("<X").workplane(centerOption="CenterOfBoundBox").center(0, special_chamfer_diff/2)
        back_face = back_face.pushPoints(dm3pts)
        block = back_face.cskHole(
            cskbd,
            cskDiameter=cskbd + 2 * chamfer_l,
            cskAngle=cska,
            depth=blind_hole_depth,
        )

    # make the alignment updents in the top
    if align_bumps is True:
        top_face = block.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(-special_chamfer_diff/2, 0)
        dm3pts = [(0, aux_hole_spacing / 2), (0, -aux_hole_spacing / 2)]
        block = (
            top_face.pushPoints(dm3pts)
            .circle(alignment_updent_diameter / 2)
            .extrude(alignment_updent_height)
        )
        block = block.faces(">Z").edges().chamfer(alignment_updent_chamfer)

    # make the dowel mouting holes
    if pfdowel is True:
        top_face = block.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(-special_chamfer_diff/2, 0)
        dm3pts = [(0, aux_hole_spacing / 2), (0, -aux_hole_spacing / 2)]
        block = (
            top_face.pushPoints(dm3pts)
            .circle(alignment_updent_diameter / 2)
            .hole(pressfit_hole_diameter, depth=pressfit_hole_depth)
        )
        block = block.faces(">Z").edges("%circle").chamfer(alignment_updent_chamfer)

    # 2x countersunk holes for screws up from the bottom
    if vertm3s is True:
        csktd = 2 * tb.c.std_screw_threads["m3"]["close_r"]
        dm3pts = [(0, aux_hole_spacing / 2), (0, -aux_hole_spacing / 2)]
        bot_face = block.faces("<Z").workplane(centerOption="CenterOfBoundBox")
        bot_face = bot_face.pushPoints(dm3pts)
        block = bot_face.cskHole(csktd, cskDiameter=length - 5, cskAngle=cska)
        # chamfer the exit holes
        top_face = block.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(-special_chamfer_diff/2, 0)
        top_face = top_face.pushPoints(dm3pts)
        block = top_face.cskHole(
            csktd, cskDiameter=csktd + 2 * chamfer_l, cskAngle=cska
        )
        
    

    return block


# only for running standalone in cq-editor
if "show_object" in locals():
    show_object(build(horzm3s=True, align_bumps=True, special_chamfer=1.6))