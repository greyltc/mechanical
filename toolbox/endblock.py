import cadquery as cq
import toolbox as tb

"""
block for mounting PCBs
"""

width = None
length = None
height = None


def build(adapter_width=30, block_length=12, block_height=19.48):
    global width, length, height
    width = adapter_width - tb.c.pcb_thickness
    length = block_length
    height = block_height
    pcb_mount_holea_z = 6.5
    pcb_mount_holeb_z = -6.5
    pcb_mount_hole_depth = 7.5
    pcb_mount_hole_x_center_from_edge = 3
    pcb_mount_hole_x = length/2-pcb_mount_hole_x_center_from_edge
    mount_hole_x = 0
    # block_dowel_hole_d = 5
    # block_dowel_hole_x = 6.5

    # build the block
    block = cq.Workplane("XY").box(length, width, height)

    block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').\
        center(pcb_mount_hole_x, pcb_mount_holea_z).\
        hole(tb.c.m2_threaded_dia, depth=pcb_mount_hole_depth)
    block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').\
        center(pcb_mount_hole_x, pcb_mount_holeb_z).\
        hole(tb.c.m2_threaded_dia, depth=pcb_mount_hole_depth)
    block = block.faces("<Y").workplane(centerOption='CenterOfBoundBox').\
        center(-pcb_mount_hole_x, pcb_mount_holea_z).\
        hole(tb.c.m2_threaded_dia, depth=pcb_mount_hole_depth)
    block = block.faces("<Y").workplane(centerOption='CenterOfBoundBox').\
        center(-pcb_mount_hole_x, pcb_mount_holeb_z).\
        hole(tb.c.m2_threaded_dia, depth=pcb_mount_hole_depth)
    # counter sunk hole for use with RS Stock No. 908-7532 machine screws
    block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').\
        center(mount_hole_x, 0).\
        cskHole(tb.c.csk_thru_dia, cskDiameter=length-1,
                cskAngle=tb.c.csk_angle, clean=True)
    # block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(mount_hole_x,0).hole(m4_threaded_diameter)
    # block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(block_dowel_hole_x,0).hole(block_dowel_hole_d)
    return block
