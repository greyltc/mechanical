import cadquery as cq

# wall thickness dims
# -X, +X, -Y, +Y
wall = (10,10,10,10)

pcb_thickness = 1.6

# clearance given around the crossbar PCBs when cutting their slots in the wall
pcb_slot_clearance = 0.1

# the height above the floor(shelf) that the endblocks hold the bottom edge of the crossbar PCBs
pcb_z_gap = 0.2

# width of the hole in the wall
in_wall_void_width = 4
in_wall_void_extra_depth = 2  # further distance below shelf level

endblock_wall_spacing = 1
endblock_thickness = 10

substrate_adapters = (30,30)
substrate_spacing = (10,10)
period = (substrate_adapters[0]+substrate_spacing[0],substrate_adapters[1]+substrate_spacing[1])
array = (4,1)

extents = [
    wall[0]+wall[1]+substrate_spacing[0]+array[0]*(substrate_adapters[0]+substrate_spacing[0]),
    wall[2]+wall[3]+substrate_spacing[1]+array[1]*(substrate_adapters[1]+substrate_spacing[1])+2*(endblock_thickness+endblock_wall_spacing)
]
# if we're doing 100% packing in X, leave some room on the outside edges for screw heads and connectors
if (substrate_spacing[0] == 0):
    extents[0] = extents[0]+2*3
    
void_extents = (extents[0]-wall[0]-wall[1], extents[1]-wall[2]-wall[3])

shelf_width = endblock_wall_spacing+endblock_thickness


wall_height = 30
shelf_height = 4
cap_thickness = 5
base_thickness = 5

middle = (
    cq.Workplane('XY')
    .box(extents[0],extents[1],wall_height,centered=[True,True,False])
    .translate([(wall[1]-wall[0])/2,(wall[3]-wall[2])/2,0])
    .moveTo(0,0)
    .rect(void_extents[0],void_extents[1],centered=True)
    .cutThruAll()
)

# this shelf holds the endblocks
_shelf = (
    cq.Workplane('XY')
    .rect(extents[0],extents[1],centered=True)
        .extrude(-shelf_height)
    .translate([(wall[1]-wall[0])/2,(wall[3]-wall[2])/2,0])
    .moveTo(0,0)
    .rect(void_extents[0],void_extents[1]-2*shelf_width,centered=True)
    .cutThruAll()
    )
middle = middle.union(_shelf)

# slot side shelf mounting block holes
middle = (
    middle.faces('<Z[1]').faces('<Y')
    .workplane(offset=shelf_height,invert=True)
    .center(0,-endblock_wall_spacing)
    .rarray(xSpacing=(period[0]), ySpacing=1,xCount=array[0],yCount=1)
    .cboreHole(1,2,1)
)
middle = (
    middle.faces('<Z[1]').faces('<Y')
    .workplane(offset=shelf_height,invert=True)
    .center(0,-endblock_wall_spacing)
    .rarray(xSpacing=(period[0]), ySpacing=1,xCount=array[0],yCount=1)
    .cboreHole(1,2,1)
)


# the in wall void
_in_wall_void = cq.Workplane('XZ').add(middle.findSolid()).faces('>Y[1]').wires().toPending().extrude(in_wall_void_width,combine=False).translate([0,in_wall_void_width/2-wall[2]/2,0])
_in_wall_void = cq.Workplane('XY').add(_in_wall_void.findSolid()).faces('-Z').wires().toPending().extrude(-in_wall_void_extra_depth)
middle = middle.cut(_in_wall_void)


# a construction tool for subtracting the PCB slots
_pcb_slot_void = (
    cq.Workplane('XY')
    .rarray(xSpacing=(period[0]), ySpacing=1,xCount=array[0],yCount=1)
    .box(pcb_thickness+2*pcb_slot_clearance, extents[1], wall_height,centered=[True,False,False])
    .translate([0,-extents[1],pcb_z_gap-pcb_slot_clearance]) # so that the slots are cut in the -Y wall
    )
middle = middle.cut(_pcb_slot_void.translate([-substrate_adapters[0]/2,0,0]))
middle = middle.cut(_pcb_slot_void.translate([ substrate_adapters[0]/2,0,0]))

#middle = cq.Workplane('ZX').add(middle.findSolid()).faces('>Y').wires().toPending().extrude(8)

show_object (middle)
