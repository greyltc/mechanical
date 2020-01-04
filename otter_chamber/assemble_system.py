#!/usr/bin/env python

# NOTE: The toolbox module's folder must be found on your PYTHONPATH
# or in a parent firectory of an item in your PYTHONPATH.
# File loads are done relative to the toolbox module's folder.
# File saves are made into the working directory.
# The working directory is set to be a directory on your PYTHONPATH
# containing this file. Failing that, it becomes pathlib.Path.cwd()

import sys
import logging
import pathlib
import cadquery as cq  # type: ignore[import]

# attempt to import the toolbox module
try:
    import toolbox as tb
except ImportError:
    pass

for element in sys.path:
    if 'tb' in locals():
        break
    this_path = pathlib.Path(str(element)).resolve()
    sys.path.insert(0, str(this_path.parent))  # look for toolbox in a parent
    try:
        import toolbox as tb  # noqa: F811
    except ImportError:
        del(sys.path[0])
    sys.path.insert(0, str(this_path.parent.joinpath('mechanical')))  # look for toolbox in a parent
    try:
        import toolbox as tb  # noqa: F811
    except ImportError:
        del(sys.path[0])

if 'tb' not in locals():
    # we failed to import toolbox
    error_string = ('Failed to import the toolbox module. '
                    "That means the toolbox module's folder is not "
                    "on your PYTHONPATH (or one of its parent dirs). "
                    f'Your PYTHONPATH is {sys.path}')
    raise(ValueError(error_string))
else:
    logger = logging.getLogger('cadbuilder')
    logger.info(f'toolbox module imported from "{tb.__file__}"')


def to_holder(this_thing, y_offset):
    """
    this puts environmental chamber design output into the
    otter holder's step file coordinate system
    """
    ret_obj = this_thing.rotate((0, 0, 0), (1, 0, 0), -90)\
        .rotate((0, 0, 0), (0, 1, 0), 90)
    ret_obj = ret_obj.translate((0, y_offset, 0))
    return ret_obj


# figure out working and top level dirs
tb.u.set_directories()

# check to see if we can/should use the "show_object" function
if "show_object" in locals():
    have_so = True
    logger.info("Probably running in a gui")
else:
    have_so = False
    logger.info("Probably running from a terminal")

# a list for holding all the things
assembly = []  # type: ignore[var-annotated] # noqa: F821

# inspected step files by hand to find when our lid mates with
# otter's holder's support surface
chamber_y_offset = 32.624 - 28.85  # 32.624-28.85=3.774

holder = tb.u.import_step(
    tb.u.tld.parent.joinpath("otter", "cad", "ref",
                             "otter_substrate_holder.step"))
assembly.extend(holder.vals())
gap4 = 35  # substrate spacing along the 4 repeat direction
gap5 = 29  # substrate spacing along the 5 repeat direction
holder_along_z = tb.u.find_length(holder, "Z")

ws = tb.u.import_step(
    tb.u.tld.parent.joinpath("environment_chamber", "build", "support.step"))
ws = to_holder(ws, chamber_y_offset)
assembly.extend(ws.vals())

lid = tb.u.import_step(
    tb.u.tld.parent.joinpath("environment_chamber", "build", "lid.step"))
lid = to_holder(lid, chamber_y_offset)
assembly.extend(lid.vals())

base = tb.u.import_step(
    tb.u.tld.parent.joinpath("environment_chamber", "build", "base.step"))
base = to_holder(base, chamber_y_offset)
assembly.extend(base.vals())
# measure the base
base_t = tb.u.find_length(base, "Z")
base_w = tb.u.find_length(base, "Y")
base_l = tb.u.find_length(base, "X")

# get the crossbar PCB step
pcb_project = "otter_crossbar"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tb.u.tld.parent.joinpath('electronics', pcb_project,
                                         '3dOut', this_stepfile_name)
crossbar = tb.u.import_step(this_stepfile)
crossbar_pcb_top_height = 19.5  # from crossbar PCB design

# get the adapter PCB step
pcb_project = "otter_substrate_adapter"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tb.u.tld.parent.joinpath('electronics', pcb_project,
                                         '3dOut', this_stepfile_name)
adapter = tb.u.import_step(this_stepfile)
adapter_width = tb.u.find_length(adapter)

# build an endblock
block = tb.endblock.build(adapter_width=adapter_width)
block = to_holder(block, chamber_y_offset)
block = block.translate((0, tb.endblock.height/2, 0))
gas_plate_thickness = 2  # thickness of the plate we'll use to redirect the gas
block_scrunch = 5.8  # move the blocks a further amount towards the center
blockA = block.translate(
    (0, 0, holder_along_z/2-gas_plate_thickness-block_scrunch-tb.endblock.length/2))
blockB = blockA.mirror('XY', (0, 0, 0))

# make a 2x crossbar + 5x adapter + 2x endblock subassembly (one row)
suba = []  # type: ignore[var-annotated] # noqa: F821
crossbarA = crossbar.translate((0, 0, -tb.c.pcb_thickness/2))
crossbarA = crossbarA.rotate((0, 0, 0), (0, 1, 0), 90)
crossbarA = crossbarA.translate((0, chamber_y_offset+crossbar_pcb_top_height, 0))
crossbarA = crossbarA.translate((-adapter_width/2, 0, 0))
crossbarB = crossbarA.translate((adapter_width, 0, 0))
suba.extend(crossbarA.vals())
suba.extend(crossbarB.vals())
adapterA = adapter.rotate((0, 0, 0), (1, 0, 0), -90)
adapterA = adapterA.translate((0, chamber_y_offset+crossbar_pcb_top_height, 0))
adapterB = adapterA.translate((0, 0, gap5))
adapterC = adapterB.translate((0, 0, gap5))
adapterD = adapterA.translate((0, 0, -gap5))
adapterE = adapterD.translate((0, 0, -gap5))
suba.extend(adapterA.vals())
suba.extend(adapterB.vals())
suba.extend(adapterC.vals())
suba.extend(adapterD.vals())
suba.extend(adapterE.vals())
suba.extend(blockA.vals())
suba.extend(blockB.vals())

# assembly.extend(suba)

# now duplicate the subassembly to its correct final locations (the 4 rows)
assembly.extend([x.translate(( 3*gap4/2, 0, 0)) for x in suba])  # noqa: E201
assembly.extend([x.translate((   gap4/2, 0, 0)) for x in suba])  # noqa: E201
assembly.extend([x.translate((  -gap4/2, 0, 0)) for x in suba])  # noqa
assembly.extend([x.translate((-3*gap4/2, 0, 0)) for x in suba])

# make a compound out of the assembly
cpnd = cq.Compound.makeCompound(assembly)

# export everything (this can take a while)
tb.u.export_step(cpnd, tb.u.wd.joinpath('assembly.step'))

if have_so:
    for thing in assembly:
        show_object(thing)  # type: ignore[name-defined] # noqa: F821
logger.info("Done!")
