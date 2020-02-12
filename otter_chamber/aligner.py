import cadquery as cq

class Aligner:
    tb = None

    def __init__(self, toolbox):
        self.tb = toolbox
        tb = toolbox
        s = self
        s.bw = 23.8  # part width
        s.bh = 15  # y direction length
        s.bd = 5.59  # height above endblock

        s.mount_space = tb.endblock.aux_hole_spacing  # spacing between alignment dents and mount holes
        s.below_zero = 19  # extension distance down outide of endblock

        s.chamfer_l = 0.25
        s.cska = 90

        # mount hole params
        s.mount_h_dia = tb.c.std_screw_threads["m3"]["close_r"]*2
        s.mh_from_top_of_block = tb.endblock.back_aux_hole_from_top
        s.mount_csk_dia = s.mount_h_dia+2

        # 2x alignment dent params
        s.alignment_indent_dia = tb.endblock.alignment_updent_diameter_nominal + 0.2
        s.alignment_indent_off_from_center = 0.25
        s.alignment_indent_depth = tb.endblock.alignment_updent_height + 0.2
        s.alignment_indent_chamfer = tb.endblock.alignment_updent_chamfer

        # top step params
        s.step_height = 3.3
        s.step_width = 7.5

        # alignment hole params
        s.aldia_nominal = 4
        s.aldia = s.aldia_nominal + 0.1
        s.al_chamfer = 1
        s.al_depth = 3.5+s.step_height

        # for driver hole
        s.driver_hole_d = 3 + 0.2
        
        # alignment hole position
        s.ah = [-2.5, -3.3]
        
        s.ec = [-12.5, s.step_width/2+s.ah[1]+1.625]  # edge cutout position
        s.ecd = s.step_height + 0.439  # edge cutout depth

        s.bottom_step_width = 11

    def build(self):
        """ forms the aligner geometry"""
        s = self
        wp = cq.Workplane("XY")

        # make the base object
        al = wp.rect(s.bw, s.bh, centered=True).extrude(s.bd)
        al = al.faces("<Z").rect(s.bw, s.bh, centered=True).extrude(-s.below_zero)

        # make the bottom step
        bso = s.bh - s.bottom_step_width
        al = al.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(-s.bw/2, bso).rect(s.bw, -s.bottom_step_width-1, centered=False).cutBlind(-s.below_zero)

        # make the alignment dents
        upper_bottom_face = al.faces(">Z[1]").workplane(centerOption='CenterOfBoundBox')
        upper_bottom_face = upper_bottom_face.pushPoints([(s.mount_space/2, -s.alignment_indent_off_from_center), (-s.mount_space/2, -s.alignment_indent_off_from_center)])
        al = upper_bottom_face.hole(s.alignment_indent_dia, depth=s.alignment_indent_depth)
        al = al.faces(">Z[1]").edges("%circle").chamfer(s.alignment_indent_chamfer)

        # the alignment hole
        al = al.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(s.ah[0], s.ah[1]).cskHole(s.aldia, depth=s.al_depth, cskDiameter=s.aldia+2*s.al_chamfer, cskAngle=s.cska)

        # make the top step
        al = al.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(-s.bw/2, s.bh/2-s.step_width).rect(s.bw, s.step_width, centered=False).cutBlind(-s.step_height)

        # make the mount holes
        from_mid = (s.bd+s.below_zero)/2-s.bd-s.mh_from_top_of_block
        side_face = al.faces("<Y").workplane(centerOption='CenterOfBoundBox')
        side_face = side_face.pushPoints([(s.mount_space/2, from_mid), (-s.mount_space/2, from_mid)])
        al = side_face.cskHole(s.mount_h_dia, cskDiameter=s.mount_csk_dia, cskAngle=s.cska)

        # chamfer the exits of the mount holes
        bottom_inner_face = al.faces("<Y[2]").workplane(centerOption='CenterOfBoundBox')
        bottom_inner_face = bottom_inner_face.pushPoints([(s.mount_space/2, s.below_zero/2-s.mh_from_top_of_block), (-s.mount_space/2, s.below_zero/2-s.mh_from_top_of_block)])
        al = bottom_inner_face.cskHole(s.mount_h_dia, cskDiameter=2*s.chamfer_l+s.mount_h_dia, cskAngle=s.cska)

        # chamfer almost all edges
        al = al.faces("<X").edges("%Line").chamfer(s.chamfer_l)
        al = al.faces(">X").edges("%Line").chamfer(s.chamfer_l)
        al = al.faces("<Z").edges("|X").chamfer(s.chamfer_l)
        al = al.faces(">Y").edges("|X").chamfer(s.chamfer_l)
        al = al.faces(">Z").edges("|X").chamfer(s.chamfer_l)

        # the funny edge cutout
        al = al.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(s.ec[0], s.ec[1]).hole(5, depth=s.ecd)

        # makes it a bit easier to get into position later
        al = al.translate((0, -bso/2, 0))

        # allows for the endblock to be tightened down after the aligner is on
        boreDir = cq.Vector(0, 0, 1)
        cyl_len = al.largestDimension()
        cyl = cq.Solid.makeCylinder(s.driver_hole_d/2, cyl_len, cq.Vector(0, 0, 0), boreDir).translate((0, 0, -cyl_len/2))
        al = al.cut(cyl)
        return al


# only for running standalone in cq-editor
if "show_object" in locals():
    import sys
    import os
    sys.path.insert(1, str(os.path.join(sys.path[-1], '..')))
    import toolbox

    a = Aligner(toolbox)
    show_object(a.build())
