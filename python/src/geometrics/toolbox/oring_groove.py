import cadquery as cq
import math


# path should be a wire in XY plane at Z=0
# the path the cutting tool will follow
cutter_path = (
    cq.Workplane("XY")
    .rect(150,150,centered=True)
    .extrude(1)
    .edges('|Z')
    .fillet(10)
    .faces('-Z')
    .wires()
)

# point along the path where the tool enters/exits
entry_point = [75,0,0]

# cutter crossectional shape should be in ZX
cutter_crossection = (
    cq.Workplane("ZX")
    .moveTo(-0.5, 75)
    .rect(1.0,1.0,centered=True)
    .extrude(10)
    .edges('|Y')
    .fillet(0.1)
    .faces('-Y')
    .wires()
)
cutter_crossection.ctx.pendingWires = cutter_crossection.wires().vals()


# dims from https://eicac.co.uk/O-Ring-Grooves for a 3mm oring
grove_width = 2.45  # from sharp edges
grove_depth = 2.40
bottom_radius = 0.4
top_radius = 0.25 # the important one
r = top_radius

# industry standard?
dovetail_angle = 66
# use socahtoa to tell us how to draw  the sketch for the dovetail design
a = grove_depth/math.sin(math.radians(dovetail_angle))
b = (r+r/(math.sin(math.radians(90-dovetail_angle))))/math.tan(math.radians(dovetail_angle))
p0 = (0,0)
p1 = (grove_width/2, 0)
p2 = (grove_width/2+a, -grove_depth)
p3 = (0, -grove_depth)
p1 = (grove_width/2+b, 0)
p2 = (grove_width/2+b, -r)
p3 = (grove_width/2+b-r*math.sin(math.radians(dovetail_angle)), -r-r*math.cos(math.radians(dovetail_angle)))
p4 = (grove_width/2+a, -grove_depth)
p5 = (0, -grove_depth)

cutter_sketch = cq.Workplane("XZ").lineTo(p1[0],p1[1]).lineTo(p2[0],p2[1]).lineTo(p3[0],p3[1]).lineTo(p4[0],p4[1]).lineTo(p5[0],p5[1]).close()
cutter_sketch_revolved = cutter_sketch.revolve()
ring_sketch = cq.Workplane("XZ").moveTo(p2[0],p2[1]).circle(r)
ring = ring_sketch.revolve()
cutter = cutter_sketch_revolved.cut(ring).faces('-Z').fillet(bottom_radius)

# make shape for cutter entry/exit
splitted = cutter.faces('-Z').workplane(-bottom_radius).split(keepTop=True,keepBottom=True)
top = cq.Workplane(splitted.vals()[1]).translate([0,0,grove_depth])
bot = cq.Workplane(splitted.vals()[0]).faces('+Z').wires().toPending().extrude(grove_depth)

cutter_entry_shape = bot.union(top)

cutter_split = cutter.split(keepTop=True)
cutter_crosssection = cutter_split.faces('+Y')
cutter_crosssection_shift = cutter_crosssection.translate(entry_point)

to_sweep = cutter_crosssection_shift.wires().toPending()
sweep_result = to_sweep.sweep(cutter_path, combine=False)

#show_object(cutter_sketch)
#show_object(ring_sketch)
#show_object(cutter)
#show_object(cutter_path)
#show_object(cutter_crosssection_shift.wires())
#show_object(sweep_result)
#show_object(cutter_entry_shape)


block = (
    cq.Workplane("XY")
    .rect(200,200,centered=True)
    .extrude(-5)
    .edges('|Z')
    .fillet(3)
    .cut(sweep_result)
    .cut(cutter_entry_shape.translate(entry_point))
    )

show_object(block)
