#!/usr/bin/env python

# NOTE: The toolbox module's folder must be found on your PYTHONPATH
# or in a parent directory of an item in your PYTHONPATH.
# File loads are done relative to the toolbox module's folder.
# File saves are made into the working directory.
# The working directory is set to be a directory on your PYTHONPATH
# containing this file. Failing that, it becomes pathlib.Path.cwd()

import sys
import logging
import pathlib
import cadquery as cq  # type: ignore[import]
import aligner

# attempt to import the toolbox module
try:
    import toolbox as tb
except ImportError:
    pass

for element in sys.path:
    if "tb" in locals():
        break
    this_path = pathlib.Path(str(element)).resolve()
    sys.path.insert(0, str(this_path.parent))  # look for toolbox in a parent
    try:
        import toolbox as tb  # noqa: F811
    except ImportError:
        del sys.path[0]
    sys.path.insert(
        0, str(this_path.parent.joinpath("mechanical"))
    )  # look for toolbox in a parent
    try:
        import toolbox as tb  # noqa: F811
    except ImportError:
        del sys.path[0]

if "tb" not in locals():
    # we failed to import toolbox
    error_string = (
        "Failed to import the toolbox module. "
        "That means the toolbox module's folder is not "
        "on your PYTHONPATH (or one of its parent dirs). "
        f"Your PYTHONPATH is {sys.path}"
    )
    raise (ValueError(error_string))
else:
    logger = logging.getLogger("cadbuilder")
    logger.info(f'toolbox module imported from "{tb.__file__}"')


def to_holder(this_thing, y_offset):
    """
    this puts environmental chamber design output into the
    otter holder's step file coordinate system
    """
    ret_obj = this_thing.rotate((0, 0, 0), (1, 0, 0), -90).rotate(
        (0, 0, 0), (0, 1, 0), 90
    )
    ret_obj = ret_obj.translate((0, y_offset, 0))
    return ret_obj


# figure out working and top level dirs
tb.u.set_directories()

# import the chamber drawer
sys.path.insert(0, str(tb.u.tld.parent.joinpath("environment_chamber")))
import chamber

# import the stage mounting plate
sys.path.insert(0, str(tb.u.tld.parent.joinpath("otter_mounting_plate")))
import plate

# check to see if we can/should use the "show_object" function
if "show_object" in locals():
    have_so = True
    logger.info("Probably running in a gui")
else:
    have_so = False
    logger.info("Probably running from a terminal")

# a list for holding all the things
assembly = []  # type: ignore[var-annotated] # noqa: F821

# the otter holder step file shows its "support surface" at y = this value
# that's the reference we use to move our step files around to match it
otter_support_surface = 32.624  # read manually from the otter holder step file

# here is where our chamber's support surface is before translation to match otter
chamber_support_surface = (
    -chamber.base_o_h
    + chamber.base_h
    + chamber.base_pcb_lip_h
    + chamber.meas_assembly_h
)

# so then this is the translation we need to make for our chamber to match otter's step
chamber_y_offset = otter_support_surface - chamber_support_surface
# to check that this was calculated correctly, look at the final assembly step file,
# measure the distance between the upper adapter PCB surface and the lower surface of a substrate
# that should be 3.20 + 2.03 - 1.02 - 1.60 - 0.41 - 0.25 = 1.95mm
# meaning that there is 1.95 + 1.6 = 3.55mm between the bottom surface of a PCB and
# and the bottom surface of a substrate
# this means that the spring pins are nominally compressed
# by 0.25mm beyond their "mid-stroke" position, leaving
# 2.03-1.02-0.25 = 0.76mm before their travel is maxed out
# (when the pin sleeves crash into the substrates)

# which puts the chamber floor at
chamber_floor = (
    chamber_y_offset - chamber.base_o_h + chamber.base_h + chamber.base_pcb_lip_h
)
# (and the bottom surface chamber.base_h (12.0 mm) below that)

# import holder
holder = chamber.holder
assembly.extend(holder.vals())
gap4 = chamber.substrate_pitch_y
gap5 = chamber.substrate_pitch_x
holder_along_z = chamber.holder_along_z

# build the chamber
chamber_build = chamber.build(include_hardware=True, save_step=False, run_tests=False)
chamber_build = to_holder(chamber_build, chamber_y_offset)
assembly.extend(chamber_build.Solids())

# get the baseboard PCB step
pcb_project = "otter_baseboard"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tb.u.tld.parent.joinpath(
    "electronics", pcb_project, "3dOut", this_stepfile_name
)
baseboard = tb.u.import_step(this_stepfile)

# get the crossbar PCB step
pcb_project = "otter_crossbar"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tb.u.tld.parent.joinpath(
    "electronics", pcb_project, "3dOut", this_stepfile_name
)
crossbar = tb.u.import_step(this_stepfile)
crossbar_pcb_top_height = 19.5  # from crossbar PCB design

# get the adapter PCB step
adapter = chamber.adapter
adapter_width = chamber.adapter_width

# build an alignment endblock
ablock = tb.endblock.build(
    adapter_width=adapter_width, horzm3s=True, align_bumps=True, special_chamfer=1.6
)
ablock = to_holder(ablock, chamber_floor)
ablock = ablock.translate((0, tb.endblock.height / 2, 0))

# build the aligner
ac = aligner.Aligner(tb)
al = ac.build()
al = to_holder(al, chamber_floor)
al = al.translate((0, tb.endblock.height, 0))
al = al.rotate((0, 0, 0), (0, 1, 0), -90)
ablock.add(al)  # put them on the same workplane

# build an endblock
block = tb.endblock.build(
    adapter_width=adapter_width, horzm3s=True, align_bumps=True, special_chamfer=1.6
)
block = to_holder(block, chamber_floor)
block = block.translate((0, tb.endblock.height / 2, 0))

gas_plate_thickness = 2  # thickness of the plate we'll use to redirect the gas
block_scrunch = 5.8  # move the blocks a further amount towards the center
blockA = block.translate(
    (
        0,
        0,
        holder_along_z / 2
        - gas_plate_thickness
        - block_scrunch
        - tb.endblock.length / 2,
    )
)
blockB = blockA.mirror("XY", (0, 0, 0))
ablockA = ablock.translate(
    (
        0,
        0,
        holder_along_z / 2
        - gas_plate_thickness
        - block_scrunch
        - tb.endblock.length / 2,
    )
)
ablockB = ablockA.rotate((0, 0, 0), (0, 1, 0), 180)

# make a 2x crossbar + 5x adapter + 2x endblock subassembly (one row)
suba = []  # type: ignore[var-annotated] # noqa: F821
crossbarA = crossbar.translate((0, 0, -tb.c.pcb_thickness / 2))
crossbarA = crossbarA.rotate((0, 0, 0), (0, 1, 0), 90)
crossbarA = crossbarA.translate((0, chamber_floor + crossbar_pcb_top_height, 0))
crossbarA = crossbarA.translate((-adapter_width / 2, 0, 0))
crossbarB = crossbarA.translate((adapter_width, 0, 0))
suba.extend(crossbarA.vals())
suba.extend(crossbarB.vals())
adapterA = adapter.rotate((0, 0, 0), (1, 0, 0), -90)
adapterA = adapterA.translate((0, chamber_floor + crossbar_pcb_top_height, 0))
adapterB = adapterA.translate((0, 0, gap5))
adapterC = adapterB.translate((0, 0, gap5))
adapterD = adapterA.translate((0, 0, -gap5))
adapterE = adapterD.translate((0, 0, -gap5))
suba.extend(adapterA.vals())
suba.extend(adapterB.vals())
suba.extend(adapterC.vals())
suba.extend(adapterD.vals())
suba.extend(adapterE.vals())
subab = suba.copy()  # these two are for the rows with aligners
subac = suba.copy()
suba.extend(blockA.vals())
suba.extend(blockB.vals())
subab.extend(ablockA.vals())
subab.extend(blockB.vals())
subac.extend(blockA.vals())
subac.extend(ablockB.vals())

# assembly.extend(suba)

# now duplicate the subassembly to its correct final locations (the 4 rows)
assembly.extend([x.translate((3 * gap4 / 2, 0, 0)) for x in subac])  # noqa: E201
assembly.extend([x.translate((gap4 / 2, 0, 0)) for x in suba])  # noqa: E201
assembly.extend([x.translate((-gap4 / 2, 0, 0)) for x in suba])  # noqa
assembly.extend([x.translate((-3 * gap4 / 2, 0, 0)) for x in subab])

# now for the windblocking plate:
wb_plate_dims = [154, 17.4, 2]
mount_y_offset = -0.7
mount_x_spacing = 19
mount_d = tb.c.std_screw_threads["m3"]["close_r"]*2
wp = cq.Workplane("XY")
wb = wp.box(wb_plate_dims[0], wb_plate_dims[1], wb_plate_dims[2], centered=[True, True, True])
wb = wb.faces(">Z").workplane(centerOption="CenterOfBoundBox").center(0, mount_y_offset).rarray(mount_x_spacing, 1, 2, 1).hole(mount_d)
wb = wb.rotate((0, 0, 0), (1, 0, 0), 90)
position_magic_a = 87.5  # offset from center of chamber
position_magic_b = 0.5  # height off the chamber floor
wb = wb.translate((0, position_magic_a, wb_plate_dims[1]/2 + position_magic_b))
wb = wb.rotate((0, 0, 0), (0, 0, 1), 90)

wb1 = to_holder(wb, chamber_floor)
wb2 = wb1.mirror(mirrorPlane='ZY')
assembly.extend(wb1.vals())
assembly.extend(wb2.vals())

# workplane for mux stuff
wp = cq.Workplane("XY")

pcb_dims = [321.31, 152.4, 1.6]  # relay pcb mockup
relay_pcb = wp.box(pcb_dims[0], pcb_dims[1], pcb_dims[2], centered=[True, True, False])

# load lock chamber volume
chamber_dims = [chamber.antechamber_l, chamber.antechamber_w, chamber.antechamber_h]
chamber_volume = wp.box(
    chamber_dims[0], chamber_dims[1], chamber_dims[2], centered=[True, True, False]
)

# spacing between relay boards in the mux
inter_standoff = 13
bottom_standoff = 3
box_wall_thickness = chamber.mux_box_wall_t  # mux box wall thickness

relay_pcb1 = relay_pcb.translate((0, 0, bottom_standoff + box_wall_thickness))
relay_pcb2 = relay_pcb1.translate((0, 0, inter_standoff))
relay_pcb3 = relay_pcb2.translate((0, 0, inter_standoff))
relay_pcb4 = relay_pcb3.translate((0, 0, inter_standoff))
relay_pcb5 = relay_pcb4.translate((0, 0, inter_standoff))
del relay_pcb

mux_box_dims = [plate.mux_box_l, plate.mux_box_w, plate.mux_box_h]
top_cutouts = [150, 15]  # for cutting slots for the base pcb in the mux box
mux_box = cq.Workplane("XY").box(
    mux_box_dims[0], mux_box_dims[1], mux_box_dims[2], centered=[True, True, False]
)
mux_box = mux_box.faces(">X").shell(-box_wall_thickness)
mux_box = (
    mux_box.faces(">Z")
    .workplane()
    .rarray(1, gap4, 1, 4)
    .rect(top_cutouts[0], top_cutouts[1])
    .cutBlind(-box_wall_thickness)
)
# clearance holes for dowels
mux_box = (
    mux_box.faces("<Z")
    .workplane()
    .pushPoints(plate.dowel_xys)
    .hole(2 * plate.dowel_clearance_r, depth=box_wall_thickness)
)
# clearance holes for bolting box to stage mount if needed
mux_box = (
    mux_box.faces("<Z")
    .workplane()
    .pushPoints(plate.mux_bolt_xys)
    .hole(2 * plate.low_profile_bolt_thread_clearance_r, depth=box_wall_thickness)
)
# clearance holes for stage plate mounting bolt heads
mux_box = (
    mux_box.faces("<Z")
    .workplane()
    .pushPoints(plate.stage_plate_thread_hole_xys)
    .hole(2 * plate.low_profile_bolt_head_clearance_r, depth=box_wall_thickness)
)

# PCB mounting holes
baseboard_mounts = [
    chamber.mux_pcb_screw_xs[0] * 2,
    adapter_width,
]  # for drilling PCB mouting holes in the mux box
pmhr = tb.c.std_screw_threads["m3"]["clearance_r"]
mux_box = (
    mux_box.faces(">Z")
    .workplane(centerOption="CenterOfBoundBox")
    .rarray(1, gap4, 1, 4)
    .rect(baseboard_mounts[0], baseboard_mounts[1], forConstruction=True)
    .vertices()
    .circle(pmhr)
    .cutBlind(-box_wall_thickness)
)

# PCB dowels
baseboard_mounts = [
    chamber.mux_pcb_dowel_xs[0] * 2,
    adapter_width,
]  # for drilling PCB mouting holes in the mux box
pdhr = 4.3 / 2
mux_box = (
    mux_box.faces(">Z")
    .workplane(centerOption="CenterOfBoundBox")
    .rarray(1, gap4, 1, 4)
    .rect(baseboard_mounts[0], baseboard_mounts[1], forConstruction=True)
    .vertices()
    .circle(pdhr)
    .cutBlind(-box_wall_thickness)
)

# get the dowel model
this_stepfile = tb.u.wd.joinpath("components", "P1212.060-012.step")
dowel = tb.u.import_step(this_stepfile)
dowel = dowel.rotate((0, 0, 0), (0, 1, 0), 90)

# lid mount screw holes
mbshr = tb.c.std_screw_threads[chamber.mux_pcb_screw_size]["clearance_r"]
mux_box = (
    mux_box.faces(">Z")
    .workplane(centerOption="CenterOfBoundBox")
    .pushPoints(chamber.mux_lid_screws_xys)
    .circle(mbshr)
    .cutBlind(-box_wall_thickness)
)

baseboardA = baseboard.translate((0, gap4 / 2, mux_box_dims[2]))
baseboardB = baseboard.translate((0, -gap4 / 2, mux_box_dims[2]))
baseboardC = baseboard.translate((0, -3 * gap4 / 2, mux_box_dims[2]))
baseboardD = baseboard.translate((0, 3 * gap4 / 2, mux_box_dims[2]))

# mux box assembly
mba = []
mba.extend(mux_box.vals())

for x, y in chamber.mux_pcb_dowel_xys:
    z = tb.u.find_length(dowel, "Z") / 2 + mux_box_dims[2]
    _dowel = dowel
    _dowel = _dowel.translate((x, y, z))
    mba.extend(_dowel.vals())

mba.extend(relay_pcb1.vals())
mba.extend(relay_pcb2.vals())
mba.extend(relay_pcb3.vals())
mba.extend(relay_pcb4.vals())
mba.extend(relay_pcb5.vals())
mba.extend(baseboardA.vals())
mba.extend(baseboardB.vals())
mba.extend(baseboardC.vals())
mba.extend(baseboardD.vals())

mb = cq.Compound.makeCompound(mba)

mb = to_holder(
    mb, chamber_floor - mux_box_dims[2] - chamber.base_h - chamber.base_pcb_lip_h
)
assembly.extend(mb.Solids())

# build stage plate
plate_build = plate.build(include_hardware=True, save_step=False)
plate_y_offset = (
    chamber_floor
    - mux_box_dims[2]
    - chamber.base_h
    - chamber.base_pcb_lip_h
    - plate.mux_plate_h
)
chamber_build = to_holder(plate_build, plate_y_offset)
assembly.extend(chamber_build.Solids())

# make a compound out of the assembly
cpnd = cq.Compound.makeCompound(assembly)

# export everything (this can take a while)
save_step = True
if save_step is True:
    logger.info("Saving the big step file (this could take a while)...")
    tb.u.export_step(cpnd, tb.u.wd.joinpath("assembly.step"))

if have_so is True:
    for thing in assembly:
        show_object(thing)  # type: ignore[name-defined] # noqa: F821
logger.info("Done!")
