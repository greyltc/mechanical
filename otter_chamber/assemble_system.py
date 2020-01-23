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
otter_support_surface = 32.624  # read from the otter holder step file

# here is where our chamber's support surface is before translation to match otter
chamber_support_surface = -chamber.base_o_h + chamber.base_h + chamber.meas_assembly_h

# so then this is the translation we need to make for our chamber to match otter's step
chamber_y_offset = otter_support_surface - chamber_support_surface

# which puts the chamber floor at
chamber_floor = chamber_y_offset - chamber.base_o_h + chamber.base_h
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
ablock = tb.endblock.build(adapter_width=adapter_width, horzm3s=True, align_bumps=True)
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
block = tb.endblock.build(adapter_width=adapter_width, horzm3s=True)
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




# all this is super hacky, needs to be redone
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

baseboardA = baseboard.translate((0, gap4/2, tb.c.pcb_thickness / 2+mux_box_dims_mm[2]))
baseboardB = baseboard.translate((0, -gap4/2, tb.c.pcb_thickness / 2+mux_box_dims_mm[2]))
baseboardC = baseboard.translate((0, -3*gap4/2, tb.c.pcb_thickness / 2+mux_box_dims_mm[2]))
baseboardD = baseboard.translate((0, 3*gap4/2, tb.c.pcb_thickness / 2+mux_box_dims_mm[2]))

assembly.extend(mux_box.vals())
assembly.extend(relay_pcb1.vals())
assembly.extend(relay_pcb2.vals())
assembly.extend(relay_pcb3.vals())
assembly.extend(baseboardA.vals())
assembly.extend(baseboardB.vals())
assembly.extend(baseboardC.vals())
assembly.extend(baseboardD.vals())


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
