import cadquery as cq

bw = 23.8  # part width
bh = 15  # y direction length
bd = 5.75  # height above endblock

mount_space = 16  # spacing between alignment dents and mount holes
below_zero = 15  # extension distance down outide of endblock

chamfer_l = 0.25
cska = 90


# mount hole params
mount_h_dia = 3.2
mh_from_top_of_block = 7.5
mount_csk_dia = mount_h_dia+2

# 2x alignment dent params
alignment_indent_dia = 4
alignment_indent_off_from_center = 0.25
alignment_indent_depth = 1+0.2
alignment_indent_chamfer = 0.25

# top step params
step_height = 3.25
step_width = 7.5

# alignment hole params
aldia = 4
al_chamfer = 1
al_depth = 3.5+step_height

# for driver hole
driver_hole_d = 3 + 0.2

bottom_step_width = 11

def build():
    """ forms the aligner geometry"""
    wp = cq.Workplane("XY")

    # make the base object
    al = wp.rect(bw, bh, centered=True).extrude(bd)
    al = al.faces("<Z").rect(bw, bh, centered=True).extrude(-below_zero)

    # the edge cutout
    al = al.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(-12.5, -1.6750).hole(5, depth=step_height)

    # make the bottom step
    bso = bh - bottom_step_width
    al = al.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(-bw/2, bso).rect(bw, -bottom_step_width-1, centered=False).cutBlind(-below_zero)

    # make the alignment dents
    upper_bottom_face = al.faces(">Z[1]").workplane(centerOption='CenterOfBoundBox')
    upper_bottom_face = upper_bottom_face.pushPoints([(mount_space/2, -alignment_indent_off_from_center), (-mount_space/2, -alignment_indent_off_from_center)])
    al = upper_bottom_face.hole(alignment_indent_dia, depth=alignment_indent_depth)
    al = al.faces(">Z[1]").edges("%circle").chamfer(alignment_indent_chamfer)

    # the alignment hole
    al = al.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(-2.5, -3.3).cskHole(aldia, depth=al_depth, cskDiameter=aldia+2*al_chamfer, cskAngle=cska)

    # make the top step
    al = al.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(-bw/2, bh/2-step_width).rect(bw, step_width, centered=False).cutBlind(-step_height)

    # make the mount holes
    from_mid = (bd+below_zero)/2-bd-mh_from_top_of_block
    side_face = al.faces("<Y").workplane(centerOption='CenterOfBoundBox')
    side_face = side_face.pushPoints([(mount_space/2, from_mid), (-mount_space/2, from_mid)])
    al = side_face.cskHole(mount_h_dia, cskDiameter=mount_csk_dia, cskAngle=cska)

    # chamfer the exits of the mount holes
    bottom_inner_face = al.faces("<Y[2]").workplane(centerOption='CenterOfBoundBox')
    bottom_inner_face = bottom_inner_face.pushPoints([(mount_space/2, below_zero/2-mh_from_top_of_block), (-mount_space/2, below_zero/2-mh_from_top_of_block)])
    al = bottom_inner_face.cskHole(mount_h_dia, cskDiameter=2*chamfer_l+mount_h_dia, cskAngle=cska)

    # chamfer almost all edges
    al = al.faces("<X").edges("%Line").chamfer(chamfer_l)
    al = al.faces(">X").edges("%Line").chamfer(chamfer_l)
    al = al.faces("<Z").edges("|X").chamfer(chamfer_l)
    al = al.faces(">Y").edges("|X").chamfer(chamfer_l)
    al = al.faces(">Z").edges("|X").chamfer(chamfer_l)

    # makes it a bit easier to get into position later
    al = al.translate((0, -bso/2, 0))
    
    # allows for the endblock to be tightened down after the aligner is on
    boreDir = cq.Vector(0, 0, 1)
    cyl_len = al.largestDimension()
    cyl = cq.Solid.makeCylinder(driver_hole_d/2, cyl_len, cq.Vector(0, 0, 0), boreDir).translate((0, 0, -cyl_len/2))
    al = al.cut(cyl)
    return al

if "show_object" in locals():
    show_object(build())