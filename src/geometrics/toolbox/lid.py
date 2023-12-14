#!/usr/bin/env python3
"""Lid with an o-ring sealed window for an environment chamber."""

import logging
import math
import pathlib
from typing import Optional, Tuple

import cadquery as cq
import cq_warehouse.fastener as cqf
import cq_warehouse.extensions
import numpy as np
from geometrics.toolbox.twod_to_threed import TwoDToThreeD

import geometrics.toolbox as tb


logger = logging.getLogger("cadbuilder")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
logger.info(f'toolbox module imported from "{tb.__file__}"')

# let logger capture warnings
logging.captureWarnings(True)

# check to see if we can/should use the "show_object" function
if "show_object" in locals():
    have_so = True
    logger.info("Probably running in a gui")
else:
    have_so = False
    logger.info("Probably running from a terminal")


class LidAssemblyBuilder:
    """Build assemblies comprising chamber lid, window, and window support."""

    # the remaining thickness of metal in the lid beneath the blind threaded hole for
    # the screws that fasten the window support to the lid
    lid_t_under_support_screw = 1

    # the clearance beneath the screw that fastens the support to the lid in the blind
    # hole
    support_screw_air_gap = 1

    # socket clearance diameter
    # from https://roymech.org/Useful_Tables/Screws/Head_Clearances.html
    # + 1 is for clearnance
    socket_clearances = {"M3": 14 + 1, "M4": 22 + 1, "M5": 22 + 1, "M6": 26 + 1, "M8": 26 + 1}

    chamber_fillet = 2
    chamber_chamfer = 1
    blind_hole_chamfer = 0.25
    blind_hole_chamfer_angle = 90

    # o-ring parmaters
    min_oring_edge_gap = 1
    compression_ratio = 0.25
    gland_fill_ratio = 0.7

    # tolerance added to the window recess along the x- and y- axes
    window_recess_tol = 1

    # corner radius of window recess
    window_recess_r = 3

    # size of bolts fastening the window support to the lid
    support_bolt_size = "M4-0.7"

    # clearance across the diamater of all countersinks
    csink_clearance = 1

    valid_corner_bolt_styles = ["countersink", "nut"]

    # valid lengths of ISO 14581 screws according to https://www.fasteners.eu/standards/ISO/14581/
    valid_csink_bolt_lengths = [3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60]

    # amount of excess thread sticking out below lid if countersink bolts are used in
    # the corners to fasten the lid to the chamber
    csink_corner_bolt_extra_thread = 5

    def __init__(
        self,
        length: float,
        width: float,
        substrate_array_l: float,
        substrate_array_w: float,
        lid_t: float = 7,
        support_t: float = 3,
        window_t: float = 3,
        window_size: tuple[float, float] | None = None,
        corner_bolt_thread: str = "M5-0.8",
        corner_bolt_offset: float = 7.5,
        corner_bolt_style: str = "countersink",
        substrate_array_window_buffer: float = 6,
        oring_size: int = 169,
        window_aperture_offset: tuple = (0, 0),
        min_support_bolt_spacing: float = 30,
        include_hardware: bool = True,
        no_threads: bool = True,
    ):
        """Initialise the lid assembly.

        All dimentions are mm.

        Parameters
        ----------
        length : float
            Length of lid and support.
        width : float
            Width of lid and support.
        substrate_array_l : float
            Length between the outer edges of the substrate array.
        substrate_array_w : float
            Width between the outer edges of the substrate array.
        lid_t : float
            Thickness of lid.
        support_t : float
            Thickness of support.
        window_t : float
            Thickness of window.
        window_size : None or 2-tuple
            Tuple containing window length and width. Will be calculated if not provided.
        corner_bolt_thread : str
            Specification of corner bolt threads in cq-warehouse format e.g. M5-0.8
            (meaning size M5 with 0.8 mm thread pitch).
        corner_bolt_offset : float
            X- and y- axis offsets of the corner bolts from the outer edges of the
            assembly.
        corner_bolt_style : str
            Style of the corner bolt. Valid values are "nut" (create a recess for the
            nuts in the lid and support layers) and "countersink" (create a countersink
            for a countersink bolt).
        substrate_array_window_buffer : float
            Distance between the edge of the aperature in the window support to the
            outer edges of the substrate array.
        oring_size : int
            Integer corrsponding to an o-ring standard size.
        window_aperture_offset : 2-tuple of float
            Offset of the window aperature from centre along the x and y axes, i.e.
            (x_offset, y_offset).
        min_support_bolt_spacing : float
            Minimum centre-to-centre spacing between the support bolts that fasten the
            window support to lid. This is used to calculate the number of bolts
            required to fasten the support.
        include_hardware : bool
            Flag whether or not to include hardware, e.g. screws, nuts etc., in the
            assembly.
        no_threads : bool
            Flag whether or not to display threads in the model.
        """
        self.length = length
        self.width = width
        self.substrate_array_l = substrate_array_l
        self.substrate_array_w = substrate_array_w
        self.lid_t = lid_t
        self.support_t = support_t
        self.window_t = window_t
        self.window_size = window_size
        self.corner_bolt_thread = corner_bolt_thread
        self.corner_bolt_size, self.corner_bolt_pitch = corner_bolt_thread.split("-")
        self.corner_bolt_offset = corner_bolt_offset
        self.corner_bolt_style = corner_bolt_style
        self.substrate_array_window_buffer = substrate_array_window_buffer
        self.oring_size = oring_size
        self.window_aperture_offset = window_aperture_offset
        self.min_support_bolt_spacing = min_support_bolt_spacing
        self.include_hardware = include_hardware
        self.no_threads = no_threads

    def build(self, assembly: Optional[cq.Assembly] = None) -> cq.Assembly:
        """Build the assembly.

        Parameters
        ----------
        assembly : cq.Assembly
            Optionally provide and assembly for the lid assembly components to be added
            to. If no assembly is provided, a new one will be created.

        Returns
        -------
        assembly : cq.Assembly
            Assembly containing newly built lid assembly components.
        """
        if assembly is None:
            assembly = cq.Assembly(None)

        self._calculate_reusable_params()

        # build parts and add them to the assembly
        lid, chamber_nuts, orings = self._build_lid()
        support, chamber_bolts, support_bolts = self._build_support()
        assembly.add(lid, name="lid")
        assembly.add(support, name="support")
        assembly.add(self._build_window(), name="window")

        if self.include_hardware:
            if self.corner_bolt_style == "countersink":
                assembly.add(chamber_bolts.toCompound(), name="chamber_bolts")
            elif self.corner_bolt_style == "nut":
                assembly.add(chamber_nuts.toCompound(), name="chamber_nuts")
            else:
                pass
            assembly.add(orings.toCompound(), name="orings")
            assembly.add(support_bolts.toCompound(), name="support_bolts")

        return assembly

    def _get_std_csink_screw_length(self, ideal_length: float) -> float:
        """Find closest valid screw length less than or equal to the ideal required.

        Paremeters
        ----------
        ideal_length : float
            Ideal screw length in mm.

        Returns
        -------
        nearest_length : float
            Nearest valid screw legnth less than or equal to the ideal required.
        """
        return max([_ for _ in self.valid_csink_bolt_lengths if _ <= ideal_length])

    def _calculate_reusable_params(self):
        """Calculate parameters that are used by multiple parts."""
        self.corner_bolt_xys = [
            (self.length / 2 - self.corner_bolt_offset, self.width / 2 - self.corner_bolt_offset),
            (-self.length / 2 + self.corner_bolt_offset, self.width / 2 - self.corner_bolt_offset),
            (self.length / 2 - self.corner_bolt_offset, -self.width / 2 + self.corner_bolt_offset),
            (-self.length / 2 + self.corner_bolt_offset, -self.width / 2 + self.corner_bolt_offset),
        ]

        self.window_ap_l = self.substrate_array_l + 2 * self.substrate_array_window_buffer
        self.window_ap_w = self.substrate_array_w + 2 * self.substrate_array_window_buffer
        self.window_ap_r = self.substrate_array_window_buffer

        # --- lid o-ring ---
        self.oring_cs = tb.constants.std_orings[self.oring_size]["cs"]
        self.oring_id = tb.constants.std_orings[self.oring_size]["id"]

        logger.info(f"minimum o-ring id = {((2 * self.window_ap_l + 2 * self.window_ap_w + - 8 * self.window_ap_r + np.pi * 2 * self.window_ap_r) / np.pi) + 2 * self.min_oring_edge_gap} mm")
        logger.info(f"selected o-ring id = {self.oring_id} mm")

        # calculate a constant gap between the window aperture edge and the centre line of the o-ring
        oring_gap = (math.pi * (self.oring_id + self.oring_cs) - 2 * self.window_ap_l - 2 * self.window_ap_w + (8 - 2 * math.pi) * self.window_ap_r) / (2 * math.pi)

        # use it to determine the gland dimensions (these are o-ring/groove
        # centre-to-centre along each axis, not inner edge-to-edge)
        self.oring_gland_x = self.window_ap_l + 2 * oring_gap
        self.oring_gland_y = self.window_ap_w + 2 * oring_gap

        # check the uncompressed bend radius
        # if the bend radius is below the minimum, set it to the minimum and recalculate the gland dimensions
        oring_bend_r = self.window_ap_r + oring_gap - self.oring_cs / 2
        min_oring_bend_r = self.oring_cs * (tb.constants.oring_grooves["corner_r_fraction"])
        if oring_bend_r < min_oring_bend_r:
            logger.warning(f"WARNING: The o-ring bend radius with a constant edge gap is too low (actual = {oring_bend_r} mm, minimum = {min_oring_bend_r} mm). Retrying with minimum bend radius.")

            oring_bend_r = min_oring_bend_r
            oring_gap = (math.pi * (self.oring_id + self.oring_cs) - 2 * self.window_ap_l - 2 * self.window_ap_w + (8 - 2 * math.pi) * (min_oring_bend_r + self.oring_cs / 2)) / 8

            # changing the bend radius will cause the gap in the corners to be different to the sides
            self.oring_gland_x = self.window_ap_l + 2 * oring_gap
            self.oring_gland_y = self.window_ap_w + 2 * oring_gap

        # report inner wall thickness between oring gland and window aperture along sides
        oring_gland_w = tb.groovy.get_gland_width(self.oring_cs, self.compression_ratio, self.gland_fill_ratio)
        oring_ap_edge_gap = oring_gap - oring_gland_w / 2
        logger.info(f"o-ring inner wall thickness along sides = {oring_ap_edge_gap} mm")

        # report smallest inner wall thickness between oring gland and window aperture in corners
        oring_corner_gap = (1 - np.sqrt(2)) * (oring_bend_r + self.oring_cs / 2 - oring_gland_w / 2 - self.window_ap_r) + np.sqrt(2) * oring_ap_edge_gap
        logger.info(f"o-ring inner wall thickness in corners = {oring_corner_gap} mm")

        # check if wall thickness around groove is below minimum required
        if (oring_ap_edge_gap < self.min_oring_edge_gap) or (oring_corner_gap < self.min_oring_edge_gap):
            logger.warning(f"WARNING: Thin wall detected around o-ring groove (actual = {min(oring_ap_edge_gap, oring_corner_gap)} mm, minimum = {self.min_oring_edge_gap} mm).")

        # --- window ---
        if self.window_size is not None:
            self.window_l = self.window_size[0]
            self.window_w = self.window_size[1]
        else:
            self.window_l = np.ceil(self.window_ap_l + 2 * self.min_oring_edge_gap + 2 * oring_ap_edge_gap + 2 * oring_gland_w)
            self.window_w = np.ceil(self.window_ap_w + 2 * self.min_oring_edge_gap + 2 * oring_ap_edge_gap + 2 * oring_gland_w)

        logger.info(f"window length = {self.window_l} mm")
        logger.info(f"window width = {self.window_w} mm")

        self.window_recess_l = self.window_l + self.window_recess_tol
        self.window_recess_w = self.window_w + self.window_recess_tol

        # --- bolts for fastening window support to lid ---
        ideal_support_bolt_length = self.lid_t + self.support_t - self.lid_t_under_support_screw - self.support_screw_air_gap
        support_bolt_length = self._get_std_csink_screw_length(ideal_support_bolt_length)
        logger.info(f"Support bolt length = {support_bolt_length} mm")

        self.support_bolt = cqf.CounterSunkScrew(
            size=self.support_bolt_size,
            fastener_type="iso14581",
            length=support_bolt_length,
            simple=self.no_threads,
        )

        support_bolt_csink_diameter = self.support_bolt.screw_data["dk"]

        # part of drilled corner in window recess protruding beyond the edge
        recess_corner_excess = self.window_recess_r * (1 - 1 / np.sqrt(2))

        # offset of support bolt centers from the edge of the window recess
        # countersink clearance can be ignored here since recess edge is far away
        self.support_bolt_recess_offset = support_bolt_csink_diameter / 2 + recess_corner_excess

        # check if there's enough space along both axes of the window aperture to put
        # countersink screws
        # if either side perpendicular a given axis is too small, don't put bolts along that side
        support_bolts_along_y = True if ((self.length - self.window_recess_l - 2 * recess_corner_excess) / 2 - np.abs(self.window_aperture_offset[0]) > support_bolt_csink_diameter + self.csink_clearance) else False
        support_bolts_along_x = True if ((self.width - self.window_recess_w - 2 * recess_corner_excess) / 2 - np.abs(self.window_aperture_offset[1]) > support_bolt_csink_diameter + self.csink_clearance) else False

        # get bolt positions along the y-axis if required
        support_bolt_xys_along_y = []
        if support_bolts_along_y:
            support_bolt_xs_along_y = [
                -self.window_recess_l / 2 - self.support_bolt_recess_offset + self.window_aperture_offset[0],
                self.window_recess_l / 2 + self.support_bolt_recess_offset + self.window_aperture_offset[0],
            ]

            if support_bolts_along_x:
                num_support_bolts_along_y = math.floor((self.window_recess_w + 2 * self.support_bolt_recess_offset) / self.min_support_bolt_spacing) + 1
                support_bolt_ys_along_y = np.linspace(
                    -self.window_recess_w / 2 - self.support_bolt_recess_offset + self.window_aperture_offset[1],
                    self.window_recess_w / 2 + self.support_bolt_recess_offset + self.window_aperture_offset[1],
                    num_support_bolts_along_y,
                    endpoint=True,
                )
            else:
                num_support_bolts_along_y = math.floor((self.width - support_bolt_csink_diameter - self.csink_clearance - 2 * self.chamber_chamfer) / self.min_support_bolt_spacing) + 1
                support_bolt_ys_along_y = np.linspace(
                    -self.width / 2 + (support_bolt_csink_diameter + self.csink_clearance) / 2 + self.chamber_chamfer,
                    self.width / 2 - (support_bolt_csink_diameter + self.csink_clearance) / 2 - self.chamber_chamfer,
                    num_support_bolts_along_y,
                    endpoint=True,
                )

            support_bolt_xys_along_y = [(x, y) for x in support_bolt_xs_along_y for y in support_bolt_ys_along_y]

        # get bolt positions along the x-axis if required
        support_bolt_xys_along_x = []
        if support_bolts_along_x:
            support_bolt_ys_along_x = [
                -self.window_recess_w / 2 - self.support_bolt_recess_offset + self.window_aperture_offset[1],
                self.window_recess_w / 2 + self.support_bolt_recess_offset + self.window_aperture_offset[1],
            ]

            if support_bolts_along_y:
                num_support_bolts_along_x = math.floor((self.window_recess_l + 2 * self.support_bolt_recess_offset) / self.min_support_bolt_spacing) + 1
                support_bolt_xs_along_x = np.linspace(
                    -self.window_recess_l / 2 - self.support_bolt_recess_offset + self.window_aperture_offset[0],
                    self.window_recess_l / 2 + self.support_bolt_recess_offset + self.window_aperture_offset[0],
                    num_support_bolts_along_x,
                    endpoint=True,
                )
            else:
                num_support_bolts_along_x = math.floor((self.length - support_bolt_csink_diameter - self.csink_clearance - 2 * self.chamber_chamfer) / self.min_support_bolt_spacing) + 1
                support_bolt_xs_along_x = np.linspace(
                    -self.length / 2 + (support_bolt_csink_diameter + self.csink_clearance) / 2 + self.chamber_chamfer,
                    self.length / 2 - (support_bolt_csink_diameter + self.csink_clearance) / 2 - self.chamber_chamfer,
                    num_support_bolts_along_x,
                    endpoint=True,
                )

            support_bolt_xys_along_x = [(x, y) for x in support_bolt_xs_along_x for y in support_bolt_ys_along_x]

        # merge bolt position lists and pick out only those that are unique
        self.support_bolt_xys = set(support_bolt_xys_along_y + support_bolt_xys_along_x)

        # get chamber fastener
        if self.corner_bolt_style == "nut":
            # HFFN-M5-A2
            self.chamber_fastener = cqf.HexNutWithFlange(
                size=self.corner_bolt_thread,
                fastener_type="din1665",
                simple=self.no_threads,
            )
        elif self.corner_bolt_style == "countersink":
            ideal_corner_bolt_length = self.lid_t + self.support_t + self.csink_corner_bolt_extra_thread
            corner_bolt_length = self._get_std_csink_screw_length(ideal_corner_bolt_length)
            self.chamber_fastener = cqf.CounterSunkScrew(
                size=self.corner_bolt_thread,
                fastener_type="iso14581",
                length=corner_bolt_length,
                simple=self.no_threads,
            )
            logger.info(f"Corner bolt length = {corner_bolt_length} mm")
        else:
            raise ValueError(f"Invalid corner bolt style: {self.corner_bolt_style}. Valid styles are: {self.valid_corner_bolt_styles}.")

        # --- misc
        self.socket_clearance = self.socket_clearances[self.corner_bolt_size]

    def _build_lid(self) -> Tuple[cq.Workplane, cq.Assembly, cq.Assembly]:
        """Build the lid.

        Returns
        -------
        lid : cq.Workplane
            Lid object.
        chamber_nuts : cq.Assembly
            Assembly of chamber nuts.
        orings : cq.Assembly
            Assembly of o-rings.
        """
        # create hardware assemblies
        chamber_nuts = cq.Assembly(None)
        orings = cq.Assembly(None)

        # create lid plate
        lid = cq.Workplane("XY").box(self.length, self.width, self.lid_t)

        if self.corner_bolt_style == "nut":
            # make the socket clearance ears on the corners
            bolts_sink_depth = self.chamber_fastener.nut_thickness - self.support_t
            lid = lid.faces(">Z").rect(self.length, self.width, forConstruction=True).vertices().rect(self.socket_clearance + self.corner_bolt_offset * 2, self.corner_bolt_offset * 2, centered=True).cutBlind(-bolts_sink_depth)
            lid = lid.faces(">Z").rect(self.length, self.width, forConstruction=True).vertices().rect(self.corner_bolt_offset * 2, self.socket_clearance + self.corner_bolt_offset * 2, centered=True).cutBlind(-bolts_sink_depth)
            lid = lid.faces(">Z").workplane().pushPoints(self.corner_bolt_xys).circle(self.socket_clearance / 2).cutBlind(-bolts_sink_depth)

            # make the bolt holes and put on the nuts
            lid = lid.faces(">Z").workplane(offset=-bolts_sink_depth).pushPoints(self.corner_bolt_xys).clearanceHole(fastener=self.chamber_fastener, counterSunk=False, baseAssembly=chamber_nuts)

        if self.corner_bolt_style == "countersink":
            # make clearance hole for countersink bolts accounting for any screw head
            # height greater than the thickness of the support
            lid = lid.faces(">Z").workplane(offset=self.support_t).pushPoints(self.corner_bolt_xys).clearanceHole(fastener=self.chamber_fastener)

        # cut m4 blind threaded holes for window support
        # cq_warehouse blind holes have a cone cut in the end that could puncture
        # through the lid, so use standard cq holes with flat bottom
        if self.support_t < self.support_bolt.screw_data["dk"]:
            # need to add a countersink in lid for the screw head
            lid = (
                lid.faces(">Z")
                .workplane(centerOption="CenterOfBoundBox")
                .pushPoints(self.support_bolt_xys)
                .cskHole(
                    diameter=self.support_bolt.tap_hole_diameters["Soft"],
                    depth=self.lid_t - self.lid_t_under_support_screw,
                    cskDiameter=self.support_bolt.screw_data["dk"] - 2 * (self.support_t * np.tan((self.support_bolt.screw_data["a"] / 2) * np.pi / 180)),
                    cskAngle=self.support_bolt.screw_data["a"],
                )
            )
        else:
            lid = (
                lid.faces(">Z")
                .workplane(centerOption="CenterOfBoundBox")
                .pushPoints(self.support_bolt_xys)
                .hole(
                    diameter=self.support_bolt.tap_hole_diameters["Soft"],
                    depth=self.lid_t - self.lid_t_under_support_screw,
                )
            )

        # lid = lid.faces(">Z").workplane(offset=self.support_t).pushPoints(self.support_bolt_xys).tapHole(fastener=self.support_bolt, depth=self.support_bolt.length)

        # fillet corner side edges
        lid = lid.edges("|Z").fillet(self.chamber_fillet)

        # cut aperture for light transmission
        window_ap = cq.Workplane("XY").box(self.window_ap_l, self.window_ap_w, self.lid_t).edges("|Z").fillet(self.window_ap_r).translate((self.window_aperture_offset[0], self.window_aperture_offset[1], 0))
        lid = lid.cut(window_ap)

        # cut window recess
        window_recess = self._drilled_corner_cube(self.window_recess_l, self.window_recess_w, self.window_t, self.window_recess_r)
        window_recess = window_recess.translate((self.window_aperture_offset[0], self.window_aperture_offset[1], self.lid_t / 2 - self.window_t / 2))
        lid = lid.cut(window_recess)

        # cut o-ring groove
        cq.Workplane.mk_groove = tb.groovy.mk_groove

        if self.corner_bolt_style == "nut":
            lid = cq.CQ(lid.findSolid()).faces(">Z[-3]").workplane(centerOption="CenterOfBoundBox")

        if self.corner_bolt_style == "countersink":
            lid = cq.CQ(lid.findSolid()).faces(">Z[-2]").workplane(centerOption="CenterOfBoundBox")

        lid = lid.mk_groove(ring_cs=self.oring_cs, follow_pending_wires=False, ring_id=self.oring_id, gland_x=self.oring_gland_x, gland_y=self.oring_gland_y, compression_ratio=self.compression_ratio, gland_fill_ratio=self.gland_fill_ratio, hardware=orings)

        return (lid, chamber_nuts, orings)

    def _build_support(self) -> Tuple[cq.Workplane, cq.Assembly, cq.Assembly]:
        """Build the window support.

        Returns
        -------
        support : cq.Workplane
            Window support object.
        chamber_bolts : cq.Assembly
            Assembly of chamber bolts.
        support_bolts : cq.Assembly
            Assembly of support bolts.
        """
        # create hardware assemblies
        support_bolts = cq.Assembly(None)
        chamber_bolts = cq.Assembly(None)

        # create window support plate
        window_support = cq.Workplane("XY").box(self.length, self.width, self.support_t)

        # chamfer upper side edges
        window_support = window_support.edges("|X and >Z").chamfer(self.chamber_chamfer).edges("|Y and >Z").chamfer(self.chamber_chamfer)

        if self.corner_bolt_style == "nut":
            # cut corners for lid nut clearance
            edges = [
                "|Z and <X and <Y",
                "|Z and >X and <Y",
                "|Z and <X and >Y",
                "|Z and >X and >Y",
            ]
            for (x, y), e in zip(self.corner_bolt_xys, edges):
                corner = cq.Workplane("XY").box(self.socket_clearance, self.socket_clearance, self.support_t).edges(e).fillet(self.socket_clearance / 2).translate((x, y, 0))
                window_support = window_support.cut(corner)

        # fillet side edges
        window_support = window_support.edges("|Z").fillet(self.chamber_fillet)

        # cut window aperture
        window_ap = cq.Workplane("XY").box(self.window_ap_l, self.window_ap_w, self.support_t).edges("|Z").fillet(self.window_ap_r).translate((self.window_aperture_offset[0], self.window_aperture_offset[1], 0))
        window_support = window_support.cut(window_ap)

        # move up to sit above lid
        window_support = window_support.translate((0, 0, self.lid_t / 2 + self.support_t / 2))

        if self.corner_bolt_style == "countersink":
            # make clearance hole for countersink bolts
            window_support = window_support.faces(">Z").workplane(centerOption="CenterOfBoundBox").pushPoints(self.corner_bolt_xys).clearanceHole(fastener=self.chamber_fastener, baseAssembly=chamber_bolts)

        # cut countersink holes for support bolts
        window_support = window_support.faces(">Z").workplane(centerOption="CenterOfBoundBox").pushPoints(self.support_bolt_xys).clearanceHole(fastener=self.support_bolt, baseAssembly=support_bolts)

        return (window_support, chamber_bolts, support_bolts)

    def _build_window(self) -> cq.Workplane:
        """Build the window.

        Returns
        -------
        window : cq.Workplane
            Window object.
        """
        window = cq.Workplane("XY").box(self.window_l, self.window_w, self.window_t)
        window = window.translate((self.window_aperture_offset[0], self.window_aperture_offset[1], self.lid_t / 2 - self.window_t / 2))

        return window

    def _drilled_corner_cube(self, length: float, width: float, depth: float, radius: float) -> cq.Workplane:
        """Create a cube with drilled out corners that can be machined.

        Parameters
        ----------
        length : float
            cube length
        width : float
            cube width
        depth : float
            cube depth
        radius : float
            drill radius for corners

        Returns
        -------
        cube : cq.Workplane
            cube with drilled corners
        """
        cube = cq.Workplane("XY").box(length, width, depth)
        cube = cube.edges("|Z").chamfer(radius / 2)  # work around for a BUG in OCCT
        cube = cube.faces("<Z").workplane(centerOption="CenterOfBoundBox")
        cube = cube.rect(
            length - 2 * radius / np.sqrt(2),
            width - 2 * radius / np.sqrt(2),
            forConstruction=True,
        ).vertices()
        cube = cube.circle(radius)
        cube = cube.extrude(-depth)

        return cube


if (__name__ == "__main__") or (have_so is True):
    # set output parameters
    include_hardware = True
    save_step = True
    hwith = "with" if include_hardware else "without"
    ssave = "" if save_step else "not "
    logger.info(f"Building lid assembly {hwith} hardware and {ssave}saving step file...")

    # toggle wehter threads are shown in output step file
    no_threads = True

    # --- assembly parameters (i.e. x, y extents) ---
    length = 119
    width = 119

    # thickness of lid plate
    lid_t = 7

    # thickness of support plate
    support_t = 3

    # thread spec for bolts than fasten lid to base
    corner_bolt_thread = "M6-1"

    # style the corner fastener as eith "nut" with recess, or "countersink" for screw
    corner_bolt_style = "countersink"

    # corner bolt center offset from nearest x and y edges
    corner_bolt_offset = 7.5

    # substrate array parameters
    substrate_array_l = 50
    substrate_array_w = 50
    substrate_array_window_buffer = 6

    # o-ring specs
    oring_size = 2556308

    # window specs
    window_aperture_offset = (0, 0)
    window_t = 3
    window_size = (75, 75)

    # support bolt parameters
    min_support_bolt_spacing = 35

    # build the assembly
    lid_assembly_builder = LidAssemblyBuilder(
        length=length,
        width=width,
        substrate_array_l=substrate_array_l,
        substrate_array_w=substrate_array_w,
        lid_t=lid_t,
        support_t=support_t,
        window_t=window_t,
        window_size=window_size,
        corner_bolt_thread=corner_bolt_thread,
        corner_bolt_offset=corner_bolt_offset,
        corner_bolt_style=corner_bolt_style,
        substrate_array_window_buffer=substrate_array_window_buffer,
        oring_size=oring_size,
        window_aperture_offset=window_aperture_offset,
        min_support_bolt_spacing=min_support_bolt_spacing,
        include_hardware=include_hardware,
        no_threads=no_threads,
    )
    assembly = lid_assembly_builder.build()

    # move assembly to desired location
    assembly.loc = cq.Location(cq.Vector(0, 0, 35.3))

    if save_step:
        # set working directory
        try:
            wrk_dir = pathlib.Path(__file__).parent
        except Exception as e:
            wrk_dir = pathlib.Path.cwd()
        print(f"Working directory is {wrk_dir}")

        # output
        # TwoDToThreeD.outputter({"lid": {"assembly": assembly}}, wrk_dir)
        # only want step file so use original saver
        output_dir = wrk_dir.joinpath("output")
        pathlib.Path.mkdir(output_dir, exist_ok=True)
        assembly.save(str(output_dir.joinpath("lid.step")))
