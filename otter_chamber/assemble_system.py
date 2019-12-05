#!/usr/bin/env python

import cadquery as cq

# TODO: switch this design to CQ
#passthrough_step_file = "pcb_passthroughs.step"
passthrough_t = 12
passthrough_w =50
passthrough_l =168
#passthrough = cq.importers.importStep(passthrough_step_file)
#assembly.add(passthrough)

# design end blocks
pcb_thickness = 1.6
adapter_width = 25.4
block_width = adapter_width - pcb_thickness
block_length = 10
block_height = 19.48


m2_threaded_diameter = 1.7
m3_thread_depth = 10
pcb_mount_holea_z = 6.5
pcb_mount_holeb_z = -6.5
pcb_mount_hole_x = 8.5

m4_threaded_diameter = 3.3
m4_clearance_diameter = 4.5
mount_hole_x = 0

#block_dowel_hole_d = 5
#block_dowel_hole_x = 6.5

# build the block
block = cq.Workplane("XY").box(block_length, block_width, block_height)
block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').center(pcb_mount_hole_x, pcb_mount_holea_z).hole(m2_threaded_diameter)
block = block.faces(">Y").workplane(centerOption='CenterOfBoundBox').center(pcb_mount_hole_x, pcb_mount_holeb_z).hole(m2_threaded_diameter)
#block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(mount_hole_x,0).cskHole(m4_clearance_diameter,cskDiameter=8,cskAngle=82,clean=True)
block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(mount_hole_x,0).hole(m4_threaded_diameter)
#block = block.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(block_dowel_hole_x,0).hole(block_dowel_hole_d)
#with open("block.step", "w") as fh:
#    cq.exporters.exportShape(block, cq.exporters.ExportTypes.STEP , fh)


#block = block.translate((block_length/2+1,passthrough_w/2,block_height/2+passthrough_t))
#block2 = block.mirror('ZY',(passthrough_l/2,0,0))


#show_object(assembly)

#show_object(block2)

#assembly.add(block)
#
#

holder_step_file = "../../otter/cad/ref/otter_substrate_holder.step"
#chamber_corner_offset = (107.267, 133.891, 137.882)
holder = cq.importers.importStep(holder_step_file)
spacer_thickness = 0 # this is the spacer between their lid and ours
holder = holder.translate((0,-spacer_thickness,0))
#chamber = chamber.translate(chamber_corner_offset)
show_object(holder)



window_support_step_file = "../../environment_chamber/window_support.step"
base_step_file = "../../environment_chamber/base.step"
base_length = 238.02
base_width=201.2
chamber_y_offset=3.774
#chamber_y_offset=0
lid_step_file = "../../environment_chamber/lid.step"

# adjust ec thing to align with holder
def to_holder(obj):
    obj = obj.rotate((0,0,0),(1,0,0), -90).translate((-base_length/2,chamber_y_offset,base_width/2)).rotate((0,0,0),(0,1,0), 90)
    return obj

fourXspacing = 35
fiveXspacing = 29
#position blocks
blocks_offset_from_middle = block_length/2+141.4/2+1
block = block.rotate((0,0,0),(1,0,0), -90).rotate((0,0,0),(0,1,0), 90).translate((0,chamber_y_offset+block_height/2,blocks_offset_from_middle))
blockA = block.translate((3*fourXspacing/2,0,0))
blockB = block.translate((1*fourXspacing/2,0,0))
blockC = block.translate((-1*fourXspacing/2,0,0))
blockD = block.translate((-3*fourXspacing/2,0,0))
blocks = blockA.add(blockB).add(blockC).add(blockD).add(blockA.mirror('XY',(0,0,0))).add(blockB.mirror('XY',(0,0,0))).add(blockC.mirror('XY',(0,0,0))).add(blockD.mirror('XY',(0,0,0)))
blocks.add(blockA.mirror('XY',(0,0,0)))
#blocks.add(block.mirror('XY',(0,0,0)))

#block2 = block.mirror('XY',(0,0,0))
show_object(blocks)
#show_object(block2)

ws = cq.importers.importStep(window_support_step_file)
base = cq.importers.importStep(base_step_file)
lid = cq.importers.importStep(lid_step_file)
#ws = ws.rotate((0,0,0),(1,0,0), -90)
show_object(to_holder(ws))
show_object(to_holder(base))
show_object(to_holder(lid))

with open("lid.step", "w") as fh:
    cq.exporters.exportShape(to_holder(lid), cq.exporters.ExportTypes.STEP , fh)

with open("ws.step", "w") as fh:
    cq.exporters.exportShape(to_holder(ws), cq.exporters.ExportTypes.STEP , fh)
    
with open("base.step", "w") as fh:
    cq.exporters.exportShape(to_holder(base), cq.exporters.ExportTypes.STEP , fh)


pcb_project = "otter_substrate_adapter"
adapter_step_file_name = f"../../electronics/{pcb_project}/3dOut/substrate_adapter.step"
adapter = cq.importers.importStep(adapter_step_file_name)
adapter_y_offset =5.97 + 11.43+0.24+chamber_y_offset

adapter = adapter.rotate((0,0,0),(1,0,0), -90)
adapterA = adapter.translate((3*fourXspacing/2,adapter_y_offset,0))
adapterB = adapter.translate((1*fourXspacing/2,adapter_y_offset,0))
adapterC = adapter.translate((-1*fourXspacing/2,adapter_y_offset,0))
adapterD = adapter.translate((-3*fourXspacing/2,adapter_y_offset,0))

adapterE = adapter.translate((3*fourXspacing/2,adapter_y_offset,fiveXspacing))
adapterF = adapter.translate((1*fourXspacing/2,adapter_y_offset,fiveXspacing))
adapterG = adapter.translate((-1*fourXspacing/2,adapter_y_offset,fiveXspacing))
adapterH = adapter.translate((-3*fourXspacing/2,adapter_y_offset,fiveXspacing))

adapterI = adapter.translate((3*fourXspacing/2,adapter_y_offset,2*fiveXspacing))
adapterJ = adapter.translate((1*fourXspacing/2,adapter_y_offset,2*fiveXspacing))
adapterK = adapter.translate((-1*fourXspacing/2,adapter_y_offset,2*fiveXspacing))
adapterL = adapter.translate((-3*fourXspacing/2,adapter_y_offset,2*fiveXspacing))

adapterM = adapter.translate((3*fourXspacing/2,adapter_y_offset,-1*fiveXspacing))
adapterN = adapter.translate((1*fourXspacing/2,adapter_y_offset,-1*fiveXspacing))
adapterO = adapter.translate((-1*fourXspacing/2,adapter_y_offset,-1*fiveXspacing))
adapterP = adapter.translate((-3*fourXspacing/2,adapter_y_offset,-1*fiveXspacing))

adapterQ = adapter.translate((3*fourXspacing/2,adapter_y_offset,-2*fiveXspacing))
adapterR = adapter.translate((1*fourXspacing/2,adapter_y_offset,-2*fiveXspacing))
adapterS = adapter.translate((-1*fourXspacing/2,adapter_y_offset,-2*fiveXspacing))
adapterT = adapter.translate((-3*fourXspacing/2,adapter_y_offset,-2*fiveXspacing))

#with open("T.step", "w") as fh:
#    cq.exporters.exportShape(adapterT, cq.exporters.ExportTypes.STEP , fh)

#with open("L.step", "w") as fh:
#    cq.exporters.exportShape(adapterT, cq.exporters.ExportTypes.STEP , fh)



#assembly.add(adapter)
#assembly.add(adapter.translate((42.5,0,0)))
#assembly.add(adapter.translate((85,0,0)))
#
#assembly = assembly.rotate((0,0,0),(1,0,0), -90)
#assembly = assembly.translate((16, 16.5+1.6,75))
#show_object(assembly)
show_object(adapterA)
show_object(adapterB)
show_object(adapterC)
show_object(adapterD)

show_object(adapterE)
show_object(adapterF)
show_object(adapterG)
show_object(adapterH)

show_object(adapterI)
show_object(adapterJ)
show_object(adapterK)
show_object(adapterL)

show_object(adapterM)
show_object(adapterN)
show_object(adapterO)
show_object(adapterP)

show_object(adapterQ)
show_object(adapterR)
show_object(adapterS)
show_object(adapterT)

pcb_project = "otter_crossbar"
crossbar_step_file_name = f"../../electronics/{pcb_project}/3dOut/{pcb_project}.step"
crossbar = cq.importers.importStep(crossbar_step_file_name)
crossbar = crossbar.translate((0,0,-1.6/2))
crossbar = crossbar.rotate((0,0,0),(0,1,0), 90)
crossbar = crossbar.translate((0,11.43+0.24+chamber_y_offset,0))
crossbarA = crossbar.translate((-fourXspacing/2+adapter_width/2,0,0))
crossbarB = crossbar.translate((-fourXspacing/2-adapter_width/2,0,0))

crossbarC = crossbar.translate((-3*fourXspacing/2+adapter_width/2,0,0))
crossbarD = crossbar.translate((-3*fourXspacing/2-adapter_width/2,0,0))

crossbarE = crossbar.translate((fourXspacing/2+adapter_width/2,0,0))
crossbarF = crossbar.translate((fourXspacing/2-adapter_width/2,0,0))

crossbarG = crossbar.translate((3*fourXspacing/2+adapter_width/2,0,0))
crossbarH = crossbar.translate((3*fourXspacing/2-adapter_width/2,0,0))
#assembly = crossbar.translate((0,10,0))
#assembly.add(crossbar.translate((0,40,0)))

show_object(crossbarA)
show_object(crossbarB)

with open("cba.step", "w") as fh:
    cq.exporters.exportShape(crossbarA, cq.exporters.ExportTypes.STEP , fh)

with open("cbb.step", "w") as fh:
    cq.exporters.exportShape(crossbarB, cq.exporters.ExportTypes.STEP , fh)

show_object(crossbarC)
show_object(crossbarD)
show_object(crossbarE)
show_object(crossbarF)
show_object(crossbarG)
show_object(crossbarH)
