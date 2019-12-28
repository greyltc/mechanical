import cadquery as cq

"""
block for mounting PCBs
"""


def endblock():
    pcb_thickness = 1.6
    adapter_width = 30
    block_width = adapter_width - pcb_thickness
    block_length = 12
    block_height = 19.48

    m2_threaded_diameter = 1.6
    pcb_mount_holea_z = 6.5
    pcb_mount_holeb_z = -6.5
    pcb_mount_hole_depth = 7.5
    pcb_mount_hole_x_center_from_edge = 3
    pcb_mount_hole_x = block_length/2-pcb_mount_hole_x_center_from_edge

    m4_threaded_diameter = 3.3
    m4_clearance_diameter = 4.5
    m5_clearance_diameter = 5.5
    mount_hole_x = 0

    # block_dowel_hole_d = 5
    # block_dowel_hole_x = 6.5

    # build the block
    block = cq.Workplane("XY").box(block_length, block_width, block_height)

    block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').\
        center(pcb_mount_hole_x, pcb_mount_holea_z).\
        hole(m2_threaded_diameter, depth=pcb_mount_hole_depth)
    block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').\
        center(pcb_mount_hole_x, pcb_mount_holeb_z).\
        hole(m2_threaded_diameter, depth=pcb_mount_hole_depth)
    block = block.faces("<Y").workplane(centerOption='CenterOfBoundBox').\
        center(-pcb_mount_hole_x, pcb_mount_holea_z).\
        hole(m2_threaded_diameter, depth=pcb_mount_hole_depth)
    block = block.faces("<Y").workplane(centerOption='CenterOfBoundBox').\
        center(-pcb_mount_hole_x, pcb_mount_holeb_z).\
        hole(m2_threaded_diameter, depth=pcb_mount_hole_depth)
    # counter sunk hole for use with RS Stock No. 908-7532 machine screws
    block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').\
        center(mount_hole_x, 0).\
        cskHole(m5_clearance_diameter, cskDiameter=block_length-1, cskAngle=82,
                clean=True)
    # block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(mount_hole_x,0).hole(m4_threaded_diameter)
    # block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(block_dowel_hole_x,0).hole(block_dowel_hole_d)
    return block
