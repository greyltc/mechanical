import cadquery as cq
import math
import geometrics.toolbox as tb
import pathlib


class Sandwich:
    # a list of equally spaced numbers centered around zero
    def espace(self, n, spacing):
        return([(x-(n-1)/2)*spacing for x in range(n)])

    def __init__(self, leng=166, wid=50, substrate_xy=30, cutout_spacing=42.5, endblock_width=12, aux_hole_spacing=16, block_offset_from_edge_of_base=1):
        s = self
        tb.c = tb.constants

        s.leng = leng
        s.wid = wid

        s.bofeob = block_offset_from_edge_of_base

        s.clamp_holes = tb.c.std_screw_threads['m5']['close_r']*2

        #s.substrate_xy_nominal = substrate_xy_nominal
        #s.substrate_xy = s.substrate_xy_nominal + 0.20
        s.substrate_xy = substrate_xy  # edges of the alignment pins go here

        # to match the pcb thickness
        s.base_t = tb.c.pcb_thickness

        base_edge_gap = 1  # spacing around the pcb board for the PCB spacer layer
        s.base_cutouts_xy = s.substrate_xy + base_edge_gap*2

        # spacing of the three
        s.cutout_spacing = cutout_spacing
        
        # number of cutouts
        s.n_cutouts = 3
        # centers = [(-cutout_spacing, 0), (0, 0), ((cutout_spacing, 0))]

        # for connector pin cutouts
        s.pin_cutd = 1
        s.pin_spacing_y = 28
        s.pin_spacing_x = 2

        # for sping pin cutouts
        s.spring_cutd = 1.9  # pin dimeter is 1.5 and the pad is 1.9
        s.spring_spacing_y = 23.5
        s.major_spring_spacing_x = 5.08
        s.minor_spring_spacing_x = 2.5

        # the inner window is to ensure there's enough space for the encapsulation
        # glass. the outer window is to make a space for a spring_layer_t thick light mask
        # for contact-side illumination masking
        s.inner_window_x = 29
        s.inner_window_y = 23
        s.outer_window_x = 32
        s.outer_window_y = 21.9

        s.spring_layer_t = 2  # 2.18 mm here gives 1mm of compression

        s.endblock_width = endblock_width
        s.end_aligner_x_spacing = s.leng - s.endblock_width - s.bofeob*2
        s.end_aligner_y_spacing = aux_hole_spacing

        # nominally there is 0.25mm between the device edge and the light mask edge
        s.alignment_diameter_nominal = 3
        s.alignment_diameter_press = s.alignment_diameter_nominal - 0.05  # no movement, alignment matters
        s.alignment_diameter_slide = s.alignment_diameter_nominal + 0.15  # needs movement, algnment matters
        s.alignment_diameter_clear = s.alignment_diameter_nominal + 0.45  # free movement, alignment does not matter
        s.alignment_pin_offset_fraction = 0.35  # percentage of the substrate dimention(up to 0.50) to offset the alignment pins to prevent device rotation

        s.holder_t = 4.5  # thickness for holder layer

        # for RS PRO silicone tubing stock number 667-8448
        #s.tube_bore = 4.8
        #s.tube_wall = 1.6
        #s.tube_OD = s.tube_bore + 2*s.tube_wall
        s.tube_OD = 4 
        s.tube_pocket_OD = s.tube_OD - 0.5 # for pressfit
        s.tube_r = s.tube_OD/2
        s.tube_splooge = 0.5  # let the tube OD splooge into the substrate_xy area by this much
        s.tube_enclosure_angle = 270  # enclose the tube by this much
        s.tube_opening_offset_from_center = s.tube_r*math.sin((360-s.tube_enclosure_angle)/2*math.pi/180)
        s.max_splooge = s.tube_r - s.tube_opening_offset_from_center

        if (s.tube_splooge >= s.max_splooge):
            raise(ValueError("Too much tube splooge."))

        s.dowel_enclosure_angle = 270
        s.holder_window_dowelside_half = s.substrate_xy/2 + (s.alignment_diameter_nominal/2 - s.alignment_diameter_nominal/2*math.sin((360-s.dowel_enclosure_angle)/2*math.pi/180))
        s.holder_window_tubeside_half = s.substrate_xy/2 + s.tube_OD/2 - s.tube_splooge - s.tube_opening_offset_from_center
        s.hwdh = s.holder_window_dowelside_half
        s.hwth = s.holder_window_tubeside_half

        # pusher downer
        s.pusher_t = 5
        s.shell_t = 2
        s.pusher_win_tol_buffer = 0.3
        s.phwdho = s.hwdh - s.pusher_win_tol_buffer
        s.phwtho = s.hwth - s.pusher_win_tol_buffer
        s.phwdhi = s.phwdho - s.shell_t
        s.phwthi = s.phwtho - s.shell_t
        s.pusher_window_outer_pline_points = [(s.phwdho, s.phwdho), (-s.phwtho, s.phwdho), (-s.phwtho, -s.phwtho), (s.phwdho, -s.phwtho)]
        s.pusher_window_inner_pline_points = [(s.phwdhi, s.phwdhi), (-s.phwthi, s.phwdhi), (-s.phwthi, -s.phwthi), (s.phwdhi, -s.phwthi)]
        s.pcham = 0.3
        s.pfill = 1
        s.elastomer_outer_d_nominal = tb.c.std_socket_screws['m5']['cap_r']*2
        s.es_dia = s.elastomer_outer_d_nominal + 0.5
        s.wingnut_hole_d = s.es_dia + 0.3

    def build(self):
        s = self
        assembly = []
        # make the spacer base layer
        sandwitch_base = cq.Workplane("XY")
        sandwitch_base = sandwitch_base.box(s.leng, s.wid, s.base_t, centered=(True, True, False))
        sandwitch_base = sandwitch_base.faces(">Z").workplane(centerOption="CenterOfBoundBox").rarray(s.cutout_spacing, 1, s.n_cutouts, 1).rect(s.base_cutouts_xy, s.base_cutouts_xy).cutThruAll()
        sandwitch_base = sandwitch_base.faces(">Z").workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, s.end_aligner_y_spacing, 2, 2).hole(s.alignment_diameter_press)
        sandwitch_base = sandwitch_base.faces(">Z").workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, 1, 2, 1).hole(s.clamp_holes)
        sandwitch_base = sandwitch_base.edges("|Z and (<Y or >Y)").fillet(s.pfill)  # round outer edges
        assembly.extend(sandwitch_base.vals())

        # make the spring spacing layer
        spring_layer = sandwitch_base.faces(">Z").workplane(centerOption="CenterOfBoundBox").box(s.leng, s.wid, s.spring_layer_t, centered=(True, True, False), combine=False)
        spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, s.end_aligner_y_spacing, 2, 2).hole(s.alignment_diameter_press)
        spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, 1, 2, 1).hole(s.clamp_holes)
        for x in s.espace(s.n_cutouts,s.cutout_spacing):  # iterate through the three positions
            spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).rect(s.inner_window_x, s.inner_window_y).cutThruAll()
            spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).rect(s.outer_window_x, s.outer_window_y).cutThruAll()
            spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).rarray(s.pin_spacing_x, s.pin_spacing_y, 12, 2).hole(s.pin_cutd)
            spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x+s.minor_spring_spacing_x/2, 0).rarray(s.major_spring_spacing_x, s.spring_spacing_y, 5, 2).hole(s.spring_cutd)
            spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x-s.minor_spring_spacing_x/2, 0).rarray(s.major_spring_spacing_x, s.spring_spacing_y, 5, 2).hole(s.spring_cutd)
            spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(s.substrate_xy/2+s.alignment_diameter_nominal/2, s.substrate_xy*s.alignment_pin_offset_fraction),(s.substrate_xy/2+s.alignment_diameter_nominal/2, -s.substrate_xy*s.alignment_pin_offset_fraction)]).hole(s.alignment_diameter_clear)
            spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(s.substrate_xy*s.alignment_pin_offset_fraction, s.substrate_xy/2+s.alignment_diameter_nominal/2),(-s.substrate_xy*s.alignment_pin_offset_fraction, s.substrate_xy/2+s.alignment_diameter_nominal/2)]).hole(s.alignment_diameter_clear)
            spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(-s.substrate_xy/2-s.tube_OD/2+s.tube_splooge, 0)]).hole(s.tube_OD)
            spring_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(0, -s.substrate_xy/2-s.tube_OD/2+s.tube_splooge)]).hole(s.tube_OD)
        spring_layer = spring_layer.edges("|Z and (<Y or >Y)").fillet(s.pfill)  # round outer edges
        assembly.extend(spring_layer.vals())

        # make the holder layer
        holder_window_pline_points = [(s.hwdh, s.hwdh), (-s.hwth, s.hwdh), (-s.hwth, -s.hwth), (s.hwdh, -s.hwth)]

        holder_layer = spring_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").box(s.leng, s.wid, s.holder_t, centered=(True, True, False), combine=False)
        holder_layer = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, 1, 2, 1).hole(s.clamp_holes)
        holder_layer = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, s.end_aligner_y_spacing, 2, 2).hole(s.alignment_diameter_press)
        for x in s.espace(s.n_cutouts,s.cutout_spacing):  # iterate through the three positions
            holder_layer = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).polyline(holder_window_pline_points).close().cutThruAll()
            holder_layer = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(s.substrate_xy/2+s.alignment_diameter_nominal/2, s.substrate_xy*s.alignment_pin_offset_fraction), (s.substrate_xy/2+s.alignment_diameter_nominal/2, -s.substrate_xy*s.alignment_pin_offset_fraction)]).hole(s.alignment_diameter_press)
            holder_layer = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(s.substrate_xy*s.alignment_pin_offset_fraction, s.substrate_xy/2+s.alignment_diameter_nominal/2), (-s.substrate_xy*s.alignment_pin_offset_fraction, s.substrate_xy/2+s.alignment_diameter_nominal/2)]).hole(s.alignment_diameter_press)
            holder_layer = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(-s.substrate_xy/2-s.tube_OD/2+s.tube_splooge, 0)]).hole(s.tube_pocket_OD)
            holder_layer = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(0, -s.substrate_xy/2-s.tube_OD/2+s.tube_splooge)]).hole(s.tube_pocket_OD)
        holder_layer = holder_layer.edges("|Z and (<Y or >Y)").fillet(s.pfill)  # round outer edges
        assembly.extend(holder_layer.vals())

        # make the pusher downer base layer
        pusher = holder_layer.faces(">Z").workplane(centerOption="CenterOfBoundBox").box(s.leng, s.wid, s.pusher_t, centered=(True, True, False), combine=False)

        # make the actual pusher downers
        for x in s.espace(s.n_cutouts,s.cutout_spacing):  # iterate through the positions
            pusher = pusher.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).polyline(s.pusher_window_outer_pline_points).close().extrude(-s.holder_t - s.pusher_t)
            pusher = pusher.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).polyline(s.pusher_window_inner_pline_points).close().cutThruAll()
            pusher = pusher.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(s.substrate_xy/2+s.alignment_diameter_nominal/2, s.substrate_xy*s.alignment_pin_offset_fraction),(s.substrate_xy/2+s.alignment_diameter_nominal/2, -s.substrate_xy*s.alignment_pin_offset_fraction)]).hole(s.alignment_diameter_clear)
            pusher = pusher.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(x, 0).pushPoints([(s.substrate_xy*s.alignment_pin_offset_fraction, s.substrate_xy/2+s.alignment_diameter_nominal/2),(-s.substrate_xy*s.alignment_pin_offset_fraction, s.substrate_xy/2+s.alignment_diameter_nominal/2)]).hole(s.alignment_diameter_clear)

        pusher = pusher.edges("|Z").fillet(s.pfill)

        # make the cutouts in the pushers for the hose pieces
        for x in s.espace(s.n_cutouts,s.cutout_spacing):  # iterate through the three positions
            pusher = pusher.faces("<Z[1]").workplane(centerOption="CenterOfBoundBox").center(x, s.phwtho).rect(s.tube_OD,s.tube_OD).cutBlind(s.pusher_t)  #cut the notches in the pusher bits
            pusher = pusher.faces("<Z[1]").workplane(centerOption="CenterOfBoundBox").center(x-s.phwtho, 0).rect(s.tube_OD,s.tube_OD).cutBlind(s.pusher_t)  #cut the notches in the pusher bits

        pusher = pusher.faces(">Z").chamfer(s.pcham)  # the bottom of the base
        pusher = pusher.faces("<Z[1]").edges("<Y").chamfer(s.pcham)  # the top of the base
        pusher = pusher.faces("<Z").chamfer(s.pcham)  # the tops of the pusher downers

        pusher = pusher.faces("<Z[1]").workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, s.end_aligner_y_spacing, 2, 2).cskHole(s.alignment_diameter_slide, cskDiameter=s.alignment_diameter_slide+4*s.pcham, cskAngle=90)
        pusher = pusher.faces(">Z"   ).workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, s.end_aligner_y_spacing, 2, 2).cskHole(s.alignment_diameter_slide, cskDiameter=s.alignment_diameter_slide+2*s.pcham, cskAngle=90)

        pusher = pusher.faces("<Z[1]").workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, 1, 2, 1).cskHole(s.wingnut_hole_d, s.wingnut_hole_d+4*s.pcham, cskAngle=90)
        pusher = pusher.faces(">Z"   ).workplane(centerOption="CenterOfBoundBox").rarray(s.end_aligner_x_spacing, 1, 2, 1).cskHole(s.wingnut_hole_d, s.wingnut_hole_d+2*s.pcham, cskAngle=90)
        assembly.extend(pusher.vals())

        cpnd = cq.Compound.makeCompound(assembly)

        return cpnd


if ("show_object" in locals()) or (__name__ == "__main__"):
    s = Sandwich(leng=166, wid=50, substrate_xy=30, cutout_spacing=35, endblock_width=12, aux_hole_spacing=16, block_offset_from_edge_of_base=1)
    cmpd = s.build()
    salads = cmpd.Solids()
    for salad in salads:
        if "show_object" in locals():  # only for running standalone in cq-editor
            show_object(salad)
            tb.utilities.export_step(salad,pathlib.Path("./salad.step"))
        elif __name__ == "__main__":
            tb.utilities.export_step()