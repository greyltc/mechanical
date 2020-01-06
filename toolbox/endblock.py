import cadquery as cq
import toolbox as tb

"""
block for mounting PCBs
"""

width: float = None  # type: ignore[assignment]
length: float = None  # type: ignore[assignment]
height: float = None  # type: ignore[assignment]


def build(adapter_width=30, block_length=12, block_height=19.5):
    global width, length, height
    width = adapter_width - tb.c.pcb_thickness
    length = block_length
    height = block_height
    # these two numbers are taken from the PCB design
    pcb_mount_hole_bottom_height = 3.5
    pcb_mount_hole_spacing = 13

    top_hole_spacing = 15

    chamfer_l = 0.5

    pcb_mount_holea_z = -block_height/2+pcb_mount_hole_bottom_height
    pcb_mount_holeb_z = pcb_mount_holea_z+pcb_mount_hole_spacing
    pcb_mount_hole_depth = 7.5
    pcb_mount_hole_x_center_from_edge = 3
    pcb_mount_hole_x = length/2-pcb_mount_hole_x_center_from_edge

    # build the block
    block = cq.Workplane("XY").box(length, width, height)

    # chamfer everything
    block = block.edges("|Z").chamfer(chamfer_l)
    block = block.edges("#Z").chamfer(chamfer_l)

    # put in the PCB mounts
    block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').\
        center(pcb_mount_hole_x, pcb_mount_holea_z).\
        hole(tb.c.std_screw_threads["m2"]["tap_r"]*2, depth=pcb_mount_hole_depth)
    block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').\
        center(pcb_mount_hole_x, pcb_mount_holeb_z).\
        hole(tb.c.std_screw_threads["m2"]["tap_r"]*2, depth=pcb_mount_hole_depth)
    block = block.faces("<Y").workplane(centerOption='CenterOfBoundBox').\
        center(-pcb_mount_hole_x, pcb_mount_holea_z).\
        hole(tb.c.std_screw_threads["m2"]["tap_r"]*2, depth=pcb_mount_hole_depth)
    block = block.faces("<Y").workplane(centerOption='CenterOfBoundBox').\
        center(-pcb_mount_hole_x, pcb_mount_holeb_z).\
        hole(tb.c.std_screw_threads["m2"]["tap_r"]*2, depth=pcb_mount_hole_depth)

    # counter sunk hole for use with RS Stock No. 908-7532 machine screws
    block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').\
        cskHole(2 * tb.c.std_screw_threads["m5"]["close_r"], cskDiameter=length-1,
                cskAngle=tb.c.std_countersinks["angle"], clean=True)

    # 2x countersunk holes for screws up from the bottom
    #bot_face = block.faces("<Z").workplane(centerOption='CenterOfBoundBox')
    #bot_face = bot_face.pushPoints([(0, top_hole_spacing/2), (0, -top_hole_spacing/2)])
    #block = bot_face. cskHole(2 * tb.c.std_screw_threads["m3"]["close_r"], cskDiameter=length-5, cskAngle=tb.c.std_countersinks["angle"], clean=True)

    return block
