import cadquery as cq
import math

leng = 166
wid = 50

substrate_xy_nominal = 30
substrate_xy = substrate_xy_nominal + 0.20  # edges of the alignment pins go here

# to match the pcb thickness
base_t = 1.6

base_cutouts_xy = substrate_xy_nominal + 2

# spacing of the three
cutout_spacing = 42.5
centers = [(-cutout_spacing,0),(0,0), ((cutout_spacing,0))]

# for connector pin cutouts
pin_cutd = 1
pin_spacing_y = 28
pin_spacing_x = 2

# for sping pin cutouts
spring_cutd = 1.6  # pin dimeter is 1.5
spring_spacing_y = 23.5
spring_spacing_x = 2.5

# the inner window is to ensure there's enough space for the encapsulation
# glass. the outer window is to make a space for a spring_layer_t thick light mask
# for contact-side illumination masking
inner_window_x = 29
inner_window_y = 23
outer_window_x = 32
outer_window_y = 21.9

spring_layer_t = 2  # 2.18 mm here gives 1mm of compression

endblock_width = 12
end_aligner_x_spacing = leng - endblock_width
end_aligner_y_spacing = 16 #TODO: aux hole spacing
#endblock_alignment_centeres= [] 

# nominally there is 0.25mm between the device edge and the light mask edge
alignment_diameter_nominal = 3
alignment_diameter_press = alignment_diameter_nominal - 0.035
alignment_diameter_slide = alignment_diameter_nominal + 0.05
alignment_diameter_clear = alignment_diameter_nominal + 0.2

holder_t = 4.5

# for RS PRO silicone tubing stock number 667-8448
tube_bore = 4.8
tube_wall = 1.6
tube_OD = tube_bore + 2*tube_wall
tube_pocket_OD = tube_OD - 0.3
tube_r = tube_OD/2
tube_splooge = 0.5  # let the tube OD splooge into the substrate_xy area by this much
tube_enclosure_angle = 270  #enclose the tube by this much
tube_opening_offset_from_center = tube_r*math.sin((360-tube_enclosure_angle)/2*math.pi/180)
max_splooge = tube_r - tube_opening_offset_from_center

if (tube_splooge >= max_splooge):
    raise(ValueError("Too much tube splooge."))

dowel_enclosure_angle = 270
holder_window_dowelside_half = substrate_xy/2 + (alignment_diameter_nominal/2 - alignment_diameter_nominal/2*math.sin((360-dowel_enclosure_angle)/2*math.pi/180))
holder_window_tubeside_half = substrate_xy/2 + tube_OD/2 - tube_splooge - tube_opening_offset_from_center
hwdh = holder_window_dowelside_half
hwth = holder_window_tubeside_half

#pusher_downer

# make the spacer base layer
sandwitch_base = cq.Workplane("XY")
sandwitch_base = sandwitch_base.box(leng, wid, base_t,centered=(True,True,False))
sbf = sandwitch_base.faces(">Z").workplane(centerOption="CenterOfBoundBox")
sandwitch_base = sbf.rarray(cutout_spacing,1,3,1).rect(base_cutouts_xy,base_cutouts_xy).cutThruAll()
sbf = sandwitch_base.faces(">Z").workplane(centerOption="CenterOfBoundBox")
sandwitch_base = sbf.rarray(end_aligner_x_spacing,end_aligner_y_spacing,2,2).circle(alignment_diameter_press/2).cutThruAll()

# make the spring spacing layer
spring_layer = sandwitch_base.faces(">Z").workplane(centerOption="CenterOfBoundBox").box(leng, wid, spring_layer_t,centered=(True,True,False), combine=False)
slf = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox")
cut_wires = []
cut_wires.extend(slf.rarray(end_aligner_x_spacing,end_aligner_y_spacing,2,2).circle(alignment_diameter_press/2).wires().all())
for x in (-cutout_spacing, 0 ,cutout_spacing): # iterate through the three positions
    slf = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x,0)
    cut_wires.extend(slf.rect(inner_window_x,inner_window_y).wires().all())
    cut_wires.extend(slf.rect(outer_window_x,outer_window_y).wires().all())
    cut_wires.extend(slf.rarray(pin_spacing_x,pin_spacing_y,12,2).circle(pin_cutd/2).wires().all())
    cut_wires.extend(slf.rarray(spring_spacing_x,spring_spacing_y,10,2).circle(spring_cutd/2).wires().all())
    cut_wires.extend(slf.pushPoints([(substrate_xy/2+alignment_diameter_nominal/2, 0)]).circle(alignment_diameter_clear/2).wires().all())
    cut_wires.extend(slf.pushPoints([(0, substrate_xy/2+alignment_diameter_nominal/2)]).circle(alignment_diameter_clear/2).wires().all())
    cut_wires.extend(slf.pushPoints([(-substrate_xy/2-tube_OD/2+tube_splooge, 0)]).circle(tube_OD/2).wires().all())
    cut_wires.extend(slf.pushPoints([(0, -substrate_xy/2-tube_OD/2+tube_splooge)]).circle(tube_OD/2).wires().all())

spring_layer.add(cut_wires)
spring_layer = spring_layer.cutThruAll()

# make the holder layer
holder_window_pline_points = [(hwdh,hwdh),(-hwth,hwdh),(-hwth,-hwth),(hwdh,-hwth)]

holder_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").box(leng, wid, holder_t, centered=(True,True,False), combine=False)
htf = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox")
cut_wires = []
cut_wires.extend(htf.rarray(end_aligner_x_spacing,end_aligner_y_spacing,2,2).circle(alignment_diameter_press/2).wires().all())
for x in (-cutout_spacing, 0 ,cutout_spacing): # iterate through the three positions
    htf = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x,0)
    cut_wires.extend(htf.polyline(holder_window_pline_points).close().wires().all())
    cut_wires.extend(htf.pushPoints([(substrate_xy/2+alignment_diameter_nominal/2, 0)]).circle(alignment_diameter_press/2).wires().all())
    cut_wires.extend(htf.pushPoints([(0, substrate_xy/2+alignment_diameter_nominal/2)]).circle(alignment_diameter_press/2).wires().all())
    cut_wires.extend(htf.pushPoints([(-substrate_xy/2-tube_OD/2+tube_splooge, 0)]).circle(tube_pocket_OD/2).wires().all())
    cut_wires.extend(htf.pushPoints([(0, -substrate_xy/2-tube_OD/2+tube_splooge)]).circle(tube_pocket_OD/2).wires().all())

holder_layer.add(cut_wires)
holder_layer = holder_layer.cutThruAll()