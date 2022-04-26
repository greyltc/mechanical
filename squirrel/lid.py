"""Lid with an o-ring sealed window for an environment chamber."""

import logging
import os
import pathlib

import cadquery as cq
import cq_warehouse.fastener as cqf
import cq_warehouse.extensions
import numpy as np

import geometrics.toolbox as tb


logger = logging.getLogger("cadbuilder")
logger.info(f'toolbox module imported from "{tb.__file__}"')

# let logger capture warnings
logging.captureWarnings(True)

# figure out working and top level dirs
tb.u.set_directories()

# create build dir if required
build_dir = os.path.join(tb.u.wd, "output")
if not os.path.exists(build_dir):
    os.mkdir(build_dir)
logger.info(f'Build directory is "{build_dir}"')


# check to see if we can/should use the "show_object" function
if "show_object" in locals():
    have_so = True
    logger.info("Probably running in a gui")
else:
    have_so = False
    logger.info("Probably running from a terminal")


# toggle wehter threads are shown in output step file
no_threads = True

# --- chamber parameters (i.e. x, y extents) ---
chamber_l = 229.0
chamber_w = 180.0


# thickness of lid plate
lid_h = 7
lid_h_under_support_screw = 1
support_screw_air_gap = 1


# thickness of support plate
support_h = 3

chamber_bolt_size = "M6-1"
chamber_bolt = cqf.SetScrew(
    size=chamber_bolt_size,
    fastener_type="iso4026",
    length=12.0,
    simple=no_threads,
)
chamber_bolt_offset = 7.5
chamber_bolt_xys = [
    (chamber_l / 2 - chamber_bolt_offset, chamber_w / 2 - chamber_bolt_offset),
    (-chamber_l / 2 + chamber_bolt_offset, chamber_w / 2 - chamber_bolt_offset),
    (chamber_l / 2 - chamber_bolt_offset, -chamber_w / 2 + chamber_bolt_offset),
    (-chamber_l / 2 + chamber_bolt_offset, -chamber_w / 2 + chamber_bolt_offset),
]

chamber_nut = cqf.HexNut(
    size=chamber_bolt_size,
    fastener_type="iso4032",
    simple=no_threads
)
chamber_nut_h = chamber_nut.nut_data["m"]
chamber_nut_w_across_points = 2 * (chamber_nut.nut_data["s"] / 2) / np.cos(30 * np.pi / 180)
chamber_nut_socket_clearance_r = (chamber_nut_w_across_points + chamber_nut.socket_clearance) / 2


# --- chamber detail ---
chamber_fillet = 1
chamber_chamfer = 1
blind_hole_chamfer = 0.25
blind_hole_chamfer_angle = 90


# substrate array
substrate_array_l = 130.35
substrate_array_w = 141.35
substrate_array_window_buffer = 5


# --- lid o-ring ---
min_oring_edge_gap = 2

lid_oring_size = 169
lid_oring_cs = tb.constants.std_orings[lid_oring_size]["cs"]
lid_oring_groove_w = tb.constants.std_orings[lid_oring_size]["groove_w"]
lid_oring_groove_h = tb.constants.std_orings[lid_oring_size]["gland_depth"]
lid_oring_id = tb.constants.std_orings[lid_oring_size]["id"]
lid_oring_id_tol = tb.constants.std_orings[lid_oring_size]["id_tol"]
lid_oring_r = lid_oring_cs * (tb.constants.oring_grooves["corner_r_fraction"] + 1)
# o-ring should be sized by outer diameter of groove because pressure is internal
lid_oring_groove_r = lid_oring_r - (lid_oring_groove_w - lid_oring_cs)

window_ap_l = substrate_array_l + 2 * substrate_array_window_buffer
window_ap_w = substrate_array_w + 2 * substrate_array_window_buffer
window_ap_r = substrate_array_window_buffer

logger.info(f"minimum o-ring id = {((2 * window_ap_l + 2 * window_ap_w + - 8 * window_ap_r + np.pi * 2 * window_ap_r) / np.pi) + 2 * min_oring_edge_gap} mm")
logger.info(f"selected o-ring id = {lid_oring_id} mm")

# gap between lid o-ring and window aperture in lid
lid_oring_ap_edge_gap = (
    np.pi * (lid_oring_id + lid_oring_id_tol)
    - 2 * (window_ap_l + window_ap_w)
    - (2 * np.pi) * (lid_oring_groove_w - lid_oring_cs)
    - (2 * np.pi - 8) * lid_oring_groove_r
) / 8

logger.info(f"o-ring inner edge gap = {lid_oring_ap_edge_gap} mm")

# gap between closest points of aperature and groove corner radii
lid_oring_corner_gap = (1 - np.sqrt(2)) * (lid_oring_groove_r - window_ap_r) + np.sqrt(
    2
) * lid_oring_ap_edge_gap

logger.info(f"o-ring corner edge gap = {lid_oring_corner_gap} mm")


# --- lid o-ring groove ---
lid_oring_i_l = window_ap_l + 2 * lid_oring_ap_edge_gap
lid_oring_i_w = window_ap_w + 2 * lid_oring_ap_edge_gap
lid_oring_o_l = lid_oring_i_l + 2 * lid_oring_groove_w
lid_oring_o_w = lid_oring_i_w + 2 * lid_oring_groove_w


# --- window ---
window_l = np.ceil(
    window_ap_l
    + 2 * min_oring_edge_gap
    + 2 * lid_oring_ap_edge_gap
    + 2 * lid_oring_groove_w
)
window_w = np.ceil(
    window_ap_w
    + 2 * min_oring_edge_gap
    + 2 * lid_oring_ap_edge_gap
    + 2 * lid_oring_groove_w
)
window_h = 3

logger.info(f"window length = {window_l} mm")
logger.info(f"window width = {window_w} mm")

window_recess_tol = 1
window_recess_l = window_l + window_recess_tol
window_recess_w = window_w + window_recess_tol
window_recess_r = 3


# --- bolts for fastening window support to lid ---
support_bolt_length = (
    lid_h + support_h - lid_h_under_support_screw - support_screw_air_gap
)
logger.info(f"Support bolt length = {support_bolt_length} mm")
support_bolt_size = "M4-0.7"
support_bolt = cqf.CounterSunkScrew(
    size=support_bolt_size,
    fastener_type="iso10642",
    length=support_bolt_length,
    simple=no_threads,
)

# # number of support bolts along each side
num_support_bolts = 4
support_bolt_spacing = (chamber_w / num_support_bolts)
support_bolt_recess_offset = 10
support_bolt_xs = [
    -window_recess_l / 2 - support_bolt_recess_offset,
    window_recess_l / 2 + support_bolt_recess_offset,
]
support_bolt_ys = np.linspace(
    -chamber_w / 2 + support_bolt_spacing / 2,
    chamber_w / 2 - support_bolt_spacing / 2,
    num_support_bolts,
    endpoint=True,
)
support_bolt_xys = [
    (x, y) for x in support_bolt_xs for y in support_bolt_ys
]





def oring_groove(inner_length, inner_width, groove_h, groove_w, inner_radius):
    """Groove for o-ring in the base.

    Parameters
    ----------
    inner_length : float or int
        internal length
    inner_width : float or int
        internal width
    groove_h : float or int
        depth of groove
    groove_w : float or int
        width of groove
    inner_radius : float or int
        internal radius

    Returns
    -------
    groove : Shape
        o-ring groove
    """
    # define outer perimeter
    outer = (
        cq.Workplane("XY")
        .box(inner_length + 2 * groove_w, inner_width + 2 * groove_w, groove_h)
        .edges("|Z")
        .fillet(inner_radius + groove_w)
    )

    # # define inner perimeter
    inner = (
        cq.Workplane("XY")
        .box(inner_length, inner_width, groove_h)
        .edges("|Z")
        .fillet(inner_radius)
    )

    return outer.cut(inner)


def drilled_corner_cube(length, width, depth, radius):
    """Create a cube with drilled out corners that can be machined.

    Parameters
    ----------
    length : float or int
        cube length
    width : float or int
        cube width
    depth : float or int
        cube depth
    radius : float or int
        drill radius for corners

    Returns
    -------
    cube : Shape
        cube with drilled corners
    """
    cube = cq.Workplane("XY").box(length, width, depth)
    cube = cube.edges('|Z').chamfer(radius/2)  # work around for a BUG in OCCT
    cube = cube.faces("<Z").workplane(centerOption="CenterOfBoundBox")
    cube = cube.rect(
        length - 2 * radius / np.sqrt(2),
        width - 2 * radius / np.sqrt(2),
        forConstruction=True,
    ).vertices()
    cube = cube.circle(radius)
    cube = cube.extrude(-depth)

    return cube


def lid(assembly, include_hardware=False):
    """Create lid of sample chamber."""
    hardware = cq.Assembly(None)

    # create lid plate
    lid = cq.Workplane("XY").box(chamber_l, chamber_w, lid_h)

    # cut corners for lid nut clearance
    edges = ["|Z and <X and <Y", "|Z and >X and <Y", "|Z and <X and >Y", "|Z and >X and >Y"]
    for (x, y), e in zip(chamber_bolt_xys, edges):
        corner = (
            cq.Workplane("XY")
            .box(
                2 * chamber_nut_socket_clearance_r,
                2 * chamber_nut_socket_clearance_r,
                chamber_nut_h - support_h
            )
            .edges(e)
            .fillet(chamber_nut_socket_clearance_r)
            .translate((x, y, lid_h / 2 - (chamber_nut_h - support_h) / 2))
        )
        lid = lid.cut(corner)

    # cut corner holes for mating lid to walls
    lid = (
        lid
        .faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints(chamber_bolt_xys)
        .hole(chamber_bolt.clearance_hole_diameters["Normal"])
    )

    # cut m4 blind threaded holes for window support
    lid = (
        lid
        .faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints(support_bolt_xys)
        .hole(
            diameter=support_bolt.tap_hole_diameters["Soft"],
            depth=lid_h - lid_h_under_support_screw,
        )
    )

    # fillet corner side edges
    lid = lid.edges("|Z").fillet(chamber_fillet)

    # create and cut window o-ring groove
    groove = oring_groove(
        lid_oring_i_l,
        lid_oring_i_w,
        lid_oring_groove_h,
        lid_oring_groove_w,
        lid_oring_groove_r,
    )
    groove = groove.translate(
        (0, 0, (lid_h / 2 - lid_oring_groove_h / 2 - window_h))
    )
    lid = lid.cut(groove)

    # # cut aperture for light transmission
    window_ap = cq.Workplane("XY").box(
        window_ap_l, window_ap_w, lid_h
    )
    window_ap = window_ap.edges("|Z").fillet(window_ap_r)
    lid = lid.cut(window_ap)

    # cut window recess
    window_recess = drilled_corner_cube(
        window_recess_l, window_recess_w, window_h, window_recess_r
    )
    window_recess = window_recess.translate((0, 0, lid_h / 2 - window_h / 2))
    lid = lid.cut(window_recess)

    assembly.add(lid, name="lid")

    if include_hardware is True:
        assembly.add(hardware.toCompound(), name="chamber_nuts")


def window_support(assembly, include_hardware=False):
    """Create window support."""
    hardware = cq.Assembly(None)

    # create window support plate
    window_support = cq.Workplane("XY").box(
        chamber_l, chamber_w, support_h
    )

    # chamfer upper side edges
    window_support = (
        window_support
        .edges("|X and >Z").chamfer(chamber_chamfer)
        .edges("|Y and >Z").chamfer(chamber_chamfer)
    )

    # cut corners for lid nut clearance
    edges = [
        "|Z and <X and <Y",
        "|Z and >X and <Y",
        "|Z and <X and >Y",
        "|Z and >X and >Y",
    ]
    for (x, y), e in zip(chamber_bolt_xys, edges):
        corner = (
            cq.Workplane("XY")
            .box(
                2 * chamber_nut_socket_clearance_r,
                2 * chamber_nut_socket_clearance_r,
                support_h
            )
            .edges(e)
            .fillet(chamber_nut_socket_clearance_r)
            .translate((x, y, 0))
        )
        window_support = window_support.cut(corner)

    # fillet side edges
    window_support = window_support.edges("|Z").fillet(chamber_fillet)

    # cut window aperture
    window_ap = (
        cq.Workplane("XY")
        .box(window_ap_l, window_ap_w, support_h)
        .edges("|Z")
        .fillet(window_ap_r)
    )
    window_support = window_support.cut(window_ap)

    # move up to sit above lid
    window_support = window_support.translate((0, 0, lid_h / 2 + support_h / 2))

    # cut countersink holes for support bolts
    window_support = (
        window_support
        .faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints(support_bolt_xys)
        .clearanceHole(fastener=support_bolt, baseAssembly=hardware)
    )

    assembly.add(window_support, name="window_support")

    if include_hardware is True:
        assembly.add(hardware.toCompound(), name="support_bolts")


def build(include_hardware=True, save_step=False):
    """Generate the lid/support assembly."""
    hwith = "with" if include_hardware else "without"
    ssave = "" if save_step else "not "
    logger.info(f"Building chamber {hwith} hardware and {ssave}saving step file...")

    # container for parts of the assembly
    assembly = cq.Assembly(None)

    # build parts
    lid(assembly, include_hardware)
    window_support(assembly, include_hardware)

    # save step
    assembly.save(str(pathlib.Path(build_dir).joinpath("lid.step")))


if (__name__ == "__main__") or (have_so is True):
    include_hardware = True
    save_step = True
    build(include_hardware=include_hardware, save_step=save_step)
