#!/usr/bin/env python3
import cadquery
from cadquery import cq, CQ
import math
import pathlib
from . import utilities as u
import logging

# setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(("%(asctime)s|%(name)s|%(levelname)s|" "%(message)s"))
ch.setFormatter(formatter)
logger.addHandler(ch)


def get_gland_height(ring_cs=1, compression_ratio: float = 0.25):
    return ring_cs * (1 - compression_ratio)


def get_gland_width(ring_cs=1, compression_ratio: float = 0.25, gland_fill_ratio: float = 0.7):
    ring_cs_area = math.pi * (ring_cs / 2) ** 2
    gland_area = ring_cs_area / gland_fill_ratio
    width = gland_area / get_gland_height(ring_cs, compression_ratio)
    logger = logging.getLogger(__name__)
    logger.info(f"Found {width} gland width")
    return width


def mk_groove(
    self: cq.Workplane,
    vdepth: float = 0,
    ring_cs: float = 0,
    follow_pending_wires: bool = True,
    ring_id: float = None,
    gland_x: float = None,
    gland_y: float = None,
    compression_ratio: float = 0.25,
    gland_fill_ratio: float = 0.7,
    clean: bool = True,
    hardware: cadquery.Assembly = None,
) -> cq.Workplane:
    """
    for cutting grooves
    set vdepth > 0 to cut a vgroove of that depth
    otherwise
    set ring_cs > 0 to cut an o-ring groove (the diameter of the cross section of the o-ring)
    follow_pending_wires = True, will mean the grooves will be cut according to pending wires/faces
    if that's false, we'll make a groove for a specific o-ring and you must set all off the following:
        ring_id, the innter diameter of the ring to be used (bore diameter)
        gland_x = the spacing in x between the centers of the gland (rounded) rectangle
        gland_y = the spacing in y between the centers of the gland (rounded) rectangle
        the fillets at the gland corners will be determined to ensure the ring fits, they will be equal
    if a hardware assembly is provided, o-oring hardware will be added to it
    """

    def _make_one_groove(wp, _wire, _vdepth, _ring_cs, _compression_ratio, _gland_fill_ratio):
        cp_tangent = _wire.tangentAt(0)  # tangent to cutter_path
        cp_start = _wire.startPoint()
        build_plane = cq.Plane(origin=cp_start, normal=cp_tangent, xDir=wp.plane.zDir)
        if _vdepth > 0:  # we'll cut a vgroove this deep
            half_profile = CQ(build_plane).polyline([(0, 0), (-_vdepth, 0), (0, _vdepth)]).close()
        elif ring_cs > 0:  # we'll cut an o-ring groove, ring_cs is the diameter of the cross section of the o-ring
            # according to https://web.archive.org/web/20220512010502/https://www.globaloring.com/o-ring-groove-design/
            gland_height = get_gland_height(_ring_cs, _compression_ratio)
            gland_width = get_gland_width(_ring_cs, _compression_ratio, _gland_fill_ratio)
            half_profile = CQ(build_plane).polyline([(0, 0), (-gland_height, 0), (-gland_height, gland_width / 2), (0, gland_width / 2)]).close()
        else:
            raise ValueError("One of vdepth or ring_cs must be larger than 0")
        cutter = half_profile.revolve(axisEnd=(1, 0, 0))
        cutter_split = cutter.split(keepTop=True)
        faces = cutter_split.faces().vals()
        for face in faces:  # find the right face to sweep with
            facenorm = face.normalAt()
            dotval = facenorm.dot(cp_tangent)
            if abs((abs(dotval) - 1)) <= 0.001:  # allow for small errors in orientation calculation
                cutter_crosssection = face
                break
        else:
            raise ValueError("Unable to find a cutter cross-section")

        # make the squished o-ring hardware
        if (ring_cs > 0) and (hardware is not None):
            ring_sweep_wire = CQ(build_plane).center(-gland_height / 2, 0).ellipse(gland_height / 2, ring_cs / 2 * (1 + _compression_ratio)).wires().toPending()
            hardware.add(ring_sweep_wire.sweep(_wire, combine=True, transition="round", isFrenet=True))

        to_sweep = CQ(cutter_crosssection).wires().toPending()
        return to_sweep.sweep(_wire).findSolid()

    s = self.findSolid()

    if follow_pending_wires:
        faces = self._getFaces()
        for face in faces:
            wire = face.outerWire()
            logger = logging.getLogger(__name__)
            logger.info(f"Made an o-ring gland for ring length {wire.Length()}mm and diameter {ring_cs}mm")
            sweep_result = _make_one_groove(wp=self, _wire=wire, _vdepth=vdepth, _ring_cs=ring_cs, _compression_ratio=compression_ratio, _gland_fill_ratio=gland_fill_ratio)
            s = s.cut(sweep_result)

            if clean:
                s = s.clean()
    else:  # we'll need to make our own path wire then, given the user specs
        # ensure the user passed in the right stuff
        assert vdepth == 0
        assert ring_cs > 0
        assert ring_id is not None
        assert gland_x is not None
        assert gland_y is not None
        wire_length = 2 * math.pi * (ring_id / 2 + ring_cs / 2)
        square_length = 2 * gland_x + 2 * gland_y
        if wire_length > square_length:
            raise ValueError("The o-ring circumference is too big for the given x and y gland dims")
        r = (wire_length - 2 * gland_x - 2 * gland_y) / (2 * math.pi - 8)
        if (2 * r > gland_x) or (2 * r > gland_y):
            raise ValueError("The o-ring circumference is too small for the given x and y gland dims")
        logger = logging.getLogger(__name__)
        logger.info(f"Using path bend radius {r}mm, that's an uncompressed cord inner radius of {r-ring_cs/2} (and the min is {ring_cs*3})")
        wire = CQ(self.plane).rect(gland_x, gland_y).wires().val()
        wire = wire.fillet2D(r, wire.Vertices())
        sweep_result = _make_one_groove(wp=self, _wire=wire, _vdepth=vdepth, _ring_cs=ring_cs, _compression_ratio=compression_ratio, _gland_fill_ratio=gland_fill_ratio)
        s = s.cut(sweep_result)

        if clean:
            s = s.clean()

    return self.newObject([s])
    # return self


def mk_dovetail_ogroove(cutter_path, entry_point):
    """makes a very special oring grove"""
    # dims from https://web.archive.org/web/20210311103938/https://eicac.co.uk/O-Ring-Grooves for a 4mm oring
    grove_width = 3.10  # from sharp edges
    grove_depth = 3.20
    bottom_radius = 0.8  # R1
    top_radius = 0.25  # r2, the important one
    r = top_radius

    # industry standard?
    dovetail_angle = 66
    # use socahtoa to tell us how to draw  the sketch for the dovetail design
    a = grove_depth / math.sin(math.radians(dovetail_angle))
    b = (r + r / (math.sin(math.radians(90 - dovetail_angle)))) / math.tan(math.radians(dovetail_angle))
    p0 = (0, 0)
    p1 = (grove_width / 2, 0)
    p2 = (grove_width / 2 + a, -grove_depth)
    p3 = (0, -grove_depth)
    p1 = (grove_width / 2 + b, 0)
    p2 = (grove_width / 2 + b, -r)
    p3 = (grove_width / 2 + b - r * math.sin(math.radians(dovetail_angle)), -r - r * math.cos(math.radians(dovetail_angle)))
    p4 = (grove_width / 2 + a, -grove_depth)
    p5 = (0, -grove_depth)

    cutter_sketch_half = cq.Workplane("XZ").polyline([p0, p1, p2, p3, p4, p5]).close()
    cutter_sketch_revolved = cutter_sketch_half.revolve()
    ring_sketch = cq.Workplane("XZ").moveTo(p2[0], p2[1]).circle(r)
    ring = ring_sketch.revolve()
    cutter = cutter_sketch_revolved.cut(ring).faces("-Z").fillet(bottom_radius)

    # make shape for cutter entry/exit
    splitted = cutter.faces("-Z").workplane(-bottom_radius).split(keepTop=True, keepBottom=True)
    top = cq.Workplane(splitted.vals()[1]).translate([0, 0, grove_depth])
    bot = cq.Workplane(splitted.vals()[0]).faces("+Z").wires().toPending().extrude(grove_depth)

    cutter_entry_shape = bot.union(top)

    cutter_split = cutter.split(keepTop=True)
    cutter_crosssection = cutter_split.faces("+Y")  # TODO do this more generally
    cutter_crosssection_shift = cutter_crosssection.translate(entry_point)

    to_sweep = cutter_crosssection_shift.wires().toPending()
    sweep_result = to_sweep.sweep(cutter_path, combine=False)
    return sweep_result, cutter_entry_shape
