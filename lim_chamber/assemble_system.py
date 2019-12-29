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

# figure out working and top level dirs
tb.u.set_directories()

# check to see if we can/should use the "show_object" function
if "show_object" in locals():
    have_so = True
    logger.info("Probbaly running in a gui")
else:
    have_so = False
    logger.info("Probbaly running from a terminal")

# a list for holding all the things
assembly = []  # type: ignore[var-annotated] # noqa: F821

# TODO: switch this part's design to CQ
base = tb.u.import_step(tb.u.tld.joinpath("lim_chamber",
                                          "pcb_passthroughs.step"))
base_t = tb.u.find_length(base, "Z")
base_w = tb.u.find_length(base, "Y")
base_l = tb.u.find_length(base, "X")

# get the adapter PCB step
pcb_project = "ox_30_by_30"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tb.u.tld.parent.joinpath('electronics', pcb_project,
                                         '3dOut', this_stepfile_name)
adapter = tb.u.import_step(this_stepfile)
adapter_width = tb.u.find_length(adapter)
adapter_spacing = 42.5
adapter = adapter.rotate((0, 0, 0), (0, 0, 1), 90)
# TODO: get rid of magic numbers here
adapter = adapter.translate((41.5, 25, 29.64+tb.c.pcb_thickness))
tb.u.export_step(adapter, tb.u.wd.joinpath(this_stepfile_name))

assembly.extend(adapter.vals())
assembly.extend(adapter.translate((adapter_spacing, 0, 0)).vals())
assembly.extend(adapter.translate((adapter_spacing*2, 0, 0)).vals())

# get the crossbar PCB step
pcb_project = "lim_crossbar"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tb.u.tld.parent.joinpath('electronics', pcb_project,
                                       '3dOut', this_stepfile_name)
crossbar = tb.u.import_step(this_stepfile)

crossbar = crossbar.translate((0, 0, -tb.c.pcb_thickness/2))
crossbar = crossbar.rotate((0, 0, 0), (1, 0, 0), 90)
# TODO: remove magic number
crossbar = crossbar.translate((0, 0, base_t+11.67))
crossbar = crossbar.translate((base_l/2, 0, 0))
crossbar = crossbar.translate((0, base_w/2-adapter_width/2, 0))
tb.u.export_step(crossbar, tb.u.wd.joinpath(this_stepfile_name))

assembly.extend(crossbar.vals())
assembly.extend(crossbar.translate((0, adapter_width, 0)).vals())

# build an endblock
block = tb.endblock.build(adapter_width=adapter_width)

# position the block
block_offset_from_edge_of_base = 1
block = block.translate((tb.endblock.length/2+block_offset_from_edge_of_base, base_w/2, tb.endblock.height/2+base_t))
tb.u.export_step(block, tb.u.wd.joinpath("block.step"))

assembly.extend(block.vals())
assembly.extend(block.mirror('ZY', (base_l/2, 0, 0)).vals())

# drill mounting holes in base
block_mount_hole_center_offset_from_edge = block_offset_from_edge_of_base + tb.endblock.length/2
block_mount_hole_x = base_l/2-block_mount_hole_center_offset_from_edge
# cbore holes for use with RS flangenut Stock No. 725-9650
base = base.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(block_mount_hole_x, 0).cboreHole(tb.c.cbore_thru_dia, cboreDiameter=tb.c.cbore_dia, cboreDepth=tb.c.cbore_depth, clean=True)
base = base.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(-block_mount_hole_x, 0).cboreHole(tb.c.cbore_thru_dia, cboreDiameter=tb.c.cbore_dia, cboreDepth=tb.c.cbore_depth, clean=True)
tb.u.export_step(base, tb.u.wd.joinpath("base_modified.step"))
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


# export everything (this can take a while)
tb.u.export_step(cpnd, tb.u.wd.joinpath('assembly.step'))

if have_so:
    for thing in assembly:
        show_object(thing)  # type: ignore[name-defined] # noqa: F821
logger.info("Done!")
