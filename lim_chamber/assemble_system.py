#!/usr/bin/env python

import cadquery as cq

pcb_project = "lim_crossbar"
crossbar_step_file_name = f"../../electronics/{pcb_project}/3dOut/{pcb_project}.step"
crossbar = cq.importers.importStep(crossbar_step_file_name)
crossbar = crossbar.translate((0,0,-1.6/2))
crossbar = crossbar.rotate((0,0,0),(1,0,0), 90)
crossbar = crossbar.translate((0,0,23.67))
crossbar = crossbar.translate((168/2,0,0))
assembly = crossbar.translate((0,10,0))
assembly.add(crossbar.translate((0,40,0)))

# TODO: switch this design to CQ
passthrough_step_file = "pcb_passthroughs.step"
passthrough_t = 12
passthrough_w =50
passthrough_l =168
passthrough = cq.importers.importStep(passthrough_step_file)
assembly.add(passthrough)

# design end blocks
pcb_thickness = 1.6
adapter_width = 30
block_width = adapter_width - pcb_thickness
block_length = 23
block_height = 20

m2_threaded_diameter = 1.7
pcb_mount_holea_z = 6.24
pcb_mount_holeb_z = -6.76
pcb_mount_hole_x = 8.5

m4_threaded_diameter = 3.3
mount_hole_x = -3.5

block_dowel_hole_d = 5
block_dowel_hole_x = 6.5

# build the block
block = (cq.Workplane("XY").box(block_length, block_width, block_height))
block = block.faces(">Y").workplane().center(pcb_mount_hole_x, pcb_mount_holeb_z).hole(m2_threaded_diameter)
block = block.faces(">Y").workplane().center(pcb_mount_hole_x, pcb_mount_holea_z).hole(m2_threaded_diameter)
block = block.faces(">Z").workplane().center(mount_hole_x,0).hole(m4_threaded_diameter)
block = block.faces(">Z").workplane().center(block_dowel_hole_x,0).hole(block_dowel_hole_d)
with open("block.step", "w") as fh:
    cq.exporters.exportShape(block, cq.exporters.ExportTypes.STEP , fh)

#position it
block = block.translate((block_length/2+1,passthrough_w/2,block_height/2+passthrough_t))
block2 = block.mirror('ZY',(passthrough_l/2,0,0))


show_object(assembly)
show_object(block)
show_object(block2)

#assembly.add(block)
#
#
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

chamber_step_file = "chamber.stp"
#chamber_corner_offset = (107.267, 133.891, 137.882)
#chamber = cq.importers.importStep(chamber_step_file)
#chamber = chamber.translate(chamber_corner_offset)
#show_object(chamber)

