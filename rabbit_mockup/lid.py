#!/usr/bin/env python3
"""Lid with an o-ring sealed window for an environment chamber."""

import pathlib

import cadquery as cq
import cq_warehouse.extensions

from geometrics.toolbox.lid import LidAssemblyBuilder


# set output parameters
include_hardware = True
save_step = True
hwith = "with" if include_hardware else "without"
ssave = "" if save_step else "not "

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
min_support_bolt_spacing = 29
support_corner_bolts = False

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
    support_corner_bolts=support_corner_bolts,
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
