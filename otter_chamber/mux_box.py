import cadquery as cq

wp = cq.Workplane("XY")

pcb_dims = [321.31, 152.4, 1.6]
relay_pcb = wp.box(pcb_dims[0], pcb_dims[1], pcb_dims[2], centered=[True, True, False])

chamber_dims = [15, 8, 6]
chamber_dims_mm = [x*25.4 for x in chamber_dims]
chamber_volume = wp.box(chamber_dims_mm[0], chamber_dims_mm[1], chamber_dims_mm[2], centered=[True, True, False])

inter_standoff = 12 

bottom_standoff = 2
box_wall_thickness = 2

relay_pcb1 = relay_pcb.translate((0,0,bottom_standoff+box_wall_thickness))
relay_pcb2 = relay_pcb1.translate((0,0,inter_standoff))
relay_pcb3 = relay_pcb2.translate((0,0,inter_standoff))

mux_box_dims = [14.5, 8, 2]
mux_box_dims_mm = [x*25.4 for x in mux_box_dims]
mux_box_dims_mm[1] = 201.2
mux_box = wp.box(mux_box_dims_mm[0], mux_box_dims_mm[1], mux_box_dims_mm[2], centered=[True, True, False])
mux_box = mux_box.faces(">X").shell(-box_wall_thickness)
top_cutouts = [140,10]
# TODO: fix this super bad hack
to_cut = cq.Workplane("XY").rarray(1,35,1,4).rect(top_cutouts[0],top_cutouts[1]).extrude(50).translate((0,0,20))

mux_box = mux_box.cut(to_cut)
#mux_box = mux_box.faces(">Z").rarray(1,35,1,4).rect(top_cutouts[0],top_cutouts[1]).extrude(100)

del to_cut

del relay_pcb