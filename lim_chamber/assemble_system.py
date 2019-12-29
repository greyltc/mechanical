#!/usr/bin/env python

# NOTE: The toolbox module's folder must be found on your PYTHONPATH
# or in a parent firectory of an item in your PYTHONPATH.
# File loads are done relative to the toolbox module's folder.
# File saves are made into the working directory.
# The working directory is set to be a directory on your PYTHONPATH
# containing this file. Failing that, it becomes pathlib.Path.cwd()

import cadquery as cq

import pathlib
import logging
import sys

# setup logging
logger = logging.getLogger('cadbuilder')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(('%(asctime)s|%(name)s|%(levelname)s|'
                               '%(message)s'))
ch.setFormatter(formatter)
logger.addHandler(ch)

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

if 'tb' not in locals():
    # we failed to import toolbox
    error_string = ('Failed to import the toolbox module. '
                    "That means the toolbox module's folder is not "
                    "on your PYTHONPATH (or one of its parent dirs). "
                    f'Your PYTHONPATH is {sys.path}')
    raise(ValueError(error_string))
else:
    logger.info(f'toolbox module imported from "{tb.__file__}"')

# figure out top level directory (tld) and working directory (wd)
# file loads are done relative to tld and saves are done into wd
tld = pathlib.Path(tb.__file__).resolve().parent.parent
logger.info(f'So the top level directory is "{tld}"')
# NOTE: I'm sure there's a better way to do this...
this_filename = "assemble_system.py"
wd = None
for element in sys.path:
    potential_wd = pathlib.Path(str(element)).resolve()
    if potential_wd.joinpath(this_filename).is_file():
        wd = potential_wd
    if wd is not None:
        break
if wd is None:
    wd = pathlib.Path.cwd()
logger.info(f'The working directory is "{wd}"')

# check to see if we can use the "show_object" function
if "show_object" in locals():
    have_so = True
    logger.info("Probbaly running in a gui")
else:
    have_so = False
    logger.info("Probbaly running from a terminal")


def export_step(to_export, file):
    with open(file, "w") as fh:
        cq.exporters.exportShape(to_export, cq.exporters.ExportTypes.STEP, fh)
        logger.info(f"Exported {file.name} to {file.parent}")


def import_step(file):
    wp = None
    if file.is_file():
        wp = cq.importers.importStep(str(file))
        logger.info(f"Imported {file}")
    else:
        logger.warn(f"Failed to import {file}")
    return wp


# finds the length of a solid object along a coordinate direction
# along can be "X", "Y" or "Z"
def find_length(thisthing, along="X"):
    length = None
    if along == "X":
        length = thisthing.faces(">X").val().Center().x-thisthing.faces("<X").\
            val().Center().x
    elif along == "Y":
        length = thisthing.faces(">Y").val().Center().y-thisthing.faces("<Y").\
            val().Center().y
    elif along == "Z":
        length = thisthing.faces(">Z").val().Center().z-thisthing.faces("<Z").\
            val().Center().z
    return length


assembly = []  # a list for holding all the things

# TODO: switch this design to CQ
base = import_step(tld.joinpath("lim_chamber", "pcb_passthroughs.step"))
base_t = find_length(base, "Z")
base_w = find_length(base, "Y")
base_l = find_length(base, "X")

# get the adapter PCB step
pcb_project = "ox_30_by_30"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tld.parent.joinpath('electronics', pcb_project,
                                    '3dOut', this_stepfile_name)
adapter = import_step(this_stepfile)
adapter_width = find_length(adapter)
adapter_spacing = 42.5
adapter = adapter.rotate((0, 0, 0), (0, 0, 1), 90)
# TODO: get rid of magic numbers here
adapter = adapter.translate((41.5, 25, 29.64+tb.c.pcb_thickness))
export_step(adapter, wd.joinpath(this_stepfile_name))

assembly.extend(adapter.vals())
assembly.extend(adapter.translate((adapter_spacing, 0, 0)).vals())
assembly.extend(adapter.translate((adapter_spacing*2, 0, 0)).vals())

# get the crossbar PCB step
pcb_project = "lim_crossbar"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tld.parent.joinpath('electronics', pcb_project,
                                    '3dOut', this_stepfile_name)
crossbar = import_step(this_stepfile)

crossbar = crossbar.translate((0, 0, -tb.c.pcb_thickness/2))
crossbar = crossbar.rotate((0, 0, 0), (1, 0, 0), 90)
# TODO: remove magic number
crossbar = crossbar.translate((0, 0, base_t+11.67))
crossbar = crossbar.translate((base_l/2, 0, 0))
crossbar = crossbar.translate((0, base_w/2-adapter_width/2, 0))
export_step(crossbar, wd.joinpath(this_stepfile_name))

assembly.extend(crossbar.vals())
assembly.extend(crossbar.translate((0, adapter_width, 0)).vals())

# build an endblock
block = tb.endblock.build(adapter_width=adapter_width)

# position the block
block_offset_from_edge_of_base = 1
block = block.translate((tb.endblock.length/2+block_offset_from_edge_of_base, base_w/2, tb.endblock.height/2+base_t))
export_step(block, wd.joinpath("block.step"))

assembly.extend(block.vals())
assembly.extend(block.mirror('ZY', (base_l/2, 0, 0)).vals())

# drill mounting holes in base
block_mount_hole_center_offset_from_edge = block_offset_from_edge_of_base + tb.endblock.length/2
block_mount_hole_x = base_l/2-block_mount_hole_center_offset_from_edge
# cbore holes for use with RS flangenut Stock No. 725-9650
base = base.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(block_mount_hole_x, 0).cboreHole(tb.c.cbore_thru_dia, cboreDiameter=tb.c.cbore_dia, cboreDepth=tb.c.cbore_depth, clean=True)
base = base.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(-block_mount_hole_x, 0).cboreHole(tb.c.cbore_thru_dia, cboreDiameter=tb.c.cbore_dia, cboreDepth=tb.c.cbore_depth, clean=True)
export_step(base, wd.joinpath("base_modified.step"))
assembly.extend(base.vals())

# assembly = assembly.rotate((0,0,0),(1,0,0), -90)
# assembly = assembly.translate((16, 16.5+1.6,75))
# show_object(assembly)

# chamber_step_file = "chamber.stp"
# chamber_corner_offset = (107.267, 133.891, 137.882)
# chamber = cq.importers.importStep(chamber_step_file)
# chamber = chamber.translate(chamber_corner_offset)
# show_object(chamber)

# make a compound out of the assembly
cpnd = cq.Compound.makeCompound(assembly)

if have_so:
    for thing in assembly:
        show_object(thing)  # noqa: F821

logger.info("Done!")
