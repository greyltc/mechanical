#!/usr/bin/env python

import cadquery as cq

import pathlib
import logging

# check that this was launched properly
# so that later we can find and load the files we need
wd = pathlib.Path.cwd()
this_filename = "assemble_system.py"
this_file = wd.joinpath(this_filename)
if not this_file.is_file():
    e_string = ('This was launched incorrectly. Your working directory is'
                f' "{wd}", but it needs to be one that contains'
                f' this script ("{this_filename}").')
    raise (ValueError(e_string))


# setup logging
logger = logging.getLogger('cad builder')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(('%(asctime)s - %(name)s - %(levelname)s -'
                               ' %(message)s'))
ch.setFormatter(formatter)
logger.addHandler(ch)

# check to see if we can use the "show_object" function
if "show_object" in locals():
    have_so = True
    logger.info("Probbaly running in a gui")
else:
    have_so = False
    logger.info("Probbaly running from a terminal")


def export_step(to_export, file):
    with open(file, "w") as fh:
        cq.exporters.exportShape(to_export, cq.exporters.ExportTypes.STEP, fh)
        logger.info(f"Exported {file.name} to {file.parent}")


def import_step(file):
    wp = cq.importers.importStep(str(file))
    logger.info(f"Imported {file.name} from {file.parent}")
    return wp


# get the crossbar PCB step
pcb_project = "lim_crossbar"
this_stepfile_name = pcb_project + ".step"
this_stepfile = wd.parent.parent.joinpath('electronics',
                                          pcb_project,
                                          '3dOut', this_stepfile_name)
crossbar = import_step(this_stepfile)
# TODO: remove magic numbers
crossbar = crossbar.translate((0, 0, -1.6/2))
crossbar = crossbar.rotate((0, 0, 0), (1, 0, 0), 90)
crossbar = crossbar.translate((0, 0, 23.67))
crossbar = crossbar.translate((168/2, 0, 0))
crossbar = crossbar.translate((0, 10, 0))
export_step(crossbar, wd.joinpath(this_stepfile_name))

assembly = crossbar  # start to build up the assembly
assembly.add(crossbar.translate((0, 30, 0)))

# TODO: switch this design to CQ & remove magic numbers
passthrough = import_step(wd.joinpath("pcb_passthroughs.step"))
passthrough_t = 12
passthrough_w = 50
passthrough_l = 168

# design end blocks
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

# position the blocks
block_offset_from_edge_of_passthrough = 1
block = block.translate((block_length/2+block_offset_from_edge_of_passthrough, passthrough_w/2, block_height/2+passthrough_t))
export_step(block, wd.joinpath("block.step"))

block2 = block.mirror('ZY', (passthrough_l/2, 0, 0))
assembly.add(block)
assembly.add(block2)

# drill mounting holes in passthrough
block_mount_hole_center_offset_from_edge = block_offset_from_edge_of_passthrough + block_length/2
block_mount_hole_x = passthrough_l/2-block_mount_hole_center_offset_from_edge
# cbore holes for use with RS flangenut Stock No. 725-9650
passthrough = passthrough.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(block_mount_hole_x, 0).cboreHole(m5_clearance_diameter, cboreDiameter=12, cboreDepth=6, clean=True)
passthrough = passthrough.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(-block_mount_hole_x, 0).cboreHole(m5_clearance_diameter, cboreDiameter=12, cboreDepth=6, clean=True)
export_step(passthrough, wd.joinpath("passthrough_modified.step"))
assembly.add(passthrough)

# get the adapterboard PCBs
pcb_project = "ox_30_by_30"
this_stepfile_name = pcb_project + ".step"
this_stepfile = wd.parent.parent.joinpath('electronics',
                                          pcb_project,
                                          '3dOut', this_stepfile_name)
adapter = import_step(this_stepfile)
# TODO: get rid of magic numbers here
adapter = adapter.rotate((0, 0, 0), (0, 0, 1), 90)
adapter = adapter.translate((41.5, 25, 29.64+1.6))
export_step(adapter, wd.joinpath(this_stepfile_name))

assembly.add(adapter)
assembly.add(adapter.translate((42.5, 0, 0)))
assembly.add(adapter.translate((85, 0, 0)))

if have_so:
    show_object(assembly)

#pcb_project = "ox_30_by_30"
#adapter_step_file_name = f"../../electronics/{pcb_project}/3dOut/{pcb_project}.step"
#adapter = cq.importers.importStep(adapter_step_file_name)
#adapter = adapter.rotate((0,0,0),(0,0,1), 90)
#adapter = adapter.translate((41.5,25,29.64))
#assembly.add(adapter)
#assembly.add(adapter.translate((42.5,0,0)))
#assembly.add(adapter.translate((85,0,0)))
#
#assembly = assembly.rotate((0,0,0),(1,0,0), -90)
#assembly = assembly.translate((16, 16.5+1.6,75))
#show_object(assembly)

#chamber_step_file = "chamber.stp"
#chamber_corner_offset = (107.267, 133.891, 137.882)
#chamber = cq.importers.importStep(chamber_step_file)
#chamber = chamber.translate(chamber_corner_offset)
#show_object(chamber)
