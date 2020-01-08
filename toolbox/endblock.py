import cadquery as cq
import toolbox as tb

"""
block for mounting PCBs
"""

width: float = None  # type: ignore[assignment]
length: float = None  # type: ignore[assignment]
height: float = None  # type: ignore[assignment]

# these two numbers are taken from the PCB design
pcb_mount_hole_bottom_height = 3.5
pcb_mount_hole_spacing = 13

chamfer_l = 0.5

aux_hole_spacing = 16
alignment_updent_diameter = 4-0.05
alignment_updent_height = 1
alignment_updent_chamfer = 0.25

back_aux_hole_from_top = 7.5

blind_hole_depth = 7.5
pcb_mount_hole_x_center_from_edge = 3

cska = tb.c.std_countersinks["angle"]


def build(adapter_width=30, block_length=12, block_height=19.5, vertm3s=False, horzm3s=False, align_bumps=False):
    """
    Builds up an endblock. dualm3s True means there will be two m3 holes through vertically
    spaced by top_hole_spacing
    horzm3s means there will twom3 mounts on the back and some dents in the top
    """
    global width, length, height

    if (vertm3s is True) and (horzm3s is True):
        raise(ValueError("Hole collision while building endblock"))

    width = adapter_width - tb.c.pcb_thickness
    length = block_length
    height = block_height

    pcb_mount_holea_z = -block_height/2+pcb_mount_hole_bottom_height
    pcb_mount_holeb_z = pcb_mount_holea_z+pcb_mount_hole_spacing

    pcb_mount_hole_x = length/2-pcb_mount_hole_x_center_from_edge

    back_aux_hole_z = block_height/2 - back_aux_hole_from_top

    # build the block
    block = cq.Workplane("XY").box(length, width, height)

    # put in the PCB mounting holes
    cskbd = tb.c.std_screw_threads["m2"]["tap_r"]*2
    block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').\
        center(pcb_mount_hole_x, pcb_mount_holea_z).\
        cskHole(cskbd, cskDiameter=cskbd+2*chamfer_l, depth=blind_hole_depth, cskAngle=cska)
    block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').\
        center(pcb_mount_hole_x, pcb_mount_holeb_z).\
        cskHole(cskbd, cskDiameter=cskbd+2*chamfer_l, depth=blind_hole_depth, cskAngle=cska)
    block = block.faces("<Y").workplane(centerOption='CenterOfBoundBox').\
        center(-pcb_mount_hole_x, pcb_mount_holea_z).\
        cskHole(cskbd, cskDiameter=cskbd+2*chamfer_l, depth=blind_hole_depth, cskAngle=cska)
    block = block.faces("<Y").workplane(centerOption='CenterOfBoundBox').\
        center(-pcb_mount_hole_x, pcb_mount_holeb_z).\
        cskHole(cskbd, cskDiameter=cskbd+2*chamfer_l, depth=blind_hole_depth, cskAngle=cska)

    # 2x countersunk holes for screws up from the bottom
    if vertm3s is True:
        csktd = 2 * tb.c.std_screw_threads["m3"]["close_r"]
        dm3pts = [(0, aux_hole_spacing/2), (0, -aux_hole_spacing/2)]
        bot_face = block.faces("<Z").workplane(centerOption='CenterOfBoundBox')
        bot_face = bot_face.pushPoints(dm3pts)
        block = bot_face.cskHole(csktd, cskDiameter=length-5, cskAngle=cska)
        # chamfer the exit holes
        top_face = block.faces(">Z").workplane(centerOption='CenterOfBoundBox')
        top_face = top_face.pushPoints(dm3pts)
        block = top_face.cskHole(csktd, cskDiameter=csktd+2*chamfer_l, cskAngle=cska)

    # base mount hole for use with RS Stock No. 908-7532 machine screws
    csktd = 2 * tb.c.std_screw_threads["m5"]["close_r"]
    block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').\
        cskHole(csktd, cskDiameter=length-1.5,
                cskAngle=cska)
    # chamfer the exit hole
    block = block.faces("<Z").workplane(centerOption='CenterOfBoundBox').\
        cskHole(csktd, cskDiameter=csktd+2*chamfer_l,
                cskAngle=cska)

    # 2x threaded countersunk holes on the back side and alignment updents in the top
    if horzm3s is True:
        cskbd = 2 * tb.c.std_screw_threads["m3"]["tap_r"]
        dm3pts = [(-aux_hole_spacing/2, back_aux_hole_z), (aux_hole_spacing/2, back_aux_hole_z)]
        back_face = block.faces("<X").workplane(centerOption='CenterOfBoundBox')
        back_face = back_face.pushPoints(dm3pts)
        block = back_face.cskHole(cskbd, cskDiameter=cskbd+2*chamfer_l, cskAngle=cska, depth=blind_hole_depth)

    # make the alignment updents in the top
    if align_bumps is True:
        top_face = block.faces(">Z").workplane(centerOption='CenterOfBoundBox')
        dm3pts = [(0, aux_hole_spacing/2), (0, -aux_hole_spacing/2)]
        block = top_face.pushPoints(dm3pts).circle(alignment_updent_diameter/2).extrude(alignment_updent_height)
        block = block.faces(">Z").edges().chamfer(alignment_updent_chamfer)

    block = block.edges("%Line").chamfer(chamfer_l)

    return block
