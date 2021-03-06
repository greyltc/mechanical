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
import sandwich

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

# check to see if we can/should use the "show_object",
if "show_object" in locals():
    have_so = True
    logger.info("Probably running in a gui")
else:
    have_so = False
    logger.info("Probably running from a terminal")

# a list for holding all the things
assembly = []  # type: ignore[var-annotated] # noqa: F821

base_t = 12
base_w = 50
base_l = 168
fillet_r = 6.35/2
chamfer_l = 0.4

window_w = 30
window_l = 120

# holes for mounting the base
base_mountx = 110
base_mounty = 40

#taken from PCB design for passthrough locations
pcb_tab_spacing = 141.66
adapter_dim = 30

block_offset_from_edge_of_base = 1

# make the base shape
base = cq.Workplane("XY").rect(base_l, base_w).extrude(base_t)
base = base.rect(window_l, window_w).cutThruAll().edges("|Z").fillet(fillet_r)

# cut the mounting holes in it
top_face = base.faces(">Z").workplane(centerOption='CenterOfBoundBox')
base = top_face.rarray(base_mountx, base_mounty, 2, 2).cboreHole(**tb.c.cb('m4'))
base = base.translate((base_l/2, base_w/2, 0))

# get the crossbar PCB step
pcb_project = "lim_crossbar"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tb.u.tld.parent.joinpath('electronics', pcb_project,
                                       '3dOut', this_stepfile_name)
crossbar = tb.u.import_step(this_stepfile)
adapter_spacing = 42.5  # from crossbar PCB design
crossbar_pcb_top_height = 19.5  # from crossbar PCB design

# get the adapter PCB step
pcb_project = "ox_30_by_30"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tb.u.tld.parent.joinpath('electronics', pcb_project,
                                         '3dOut', this_stepfile_name)
adapter = tb.u.import_step(this_stepfile)
adapter_width = tb.u.find_length(adapter)

# get the baseboard PCB step
pcb_project = "lim_baseboard"
this_stepfile_name = pcb_project + ".step"
this_stepfile = tb.u.tld.parent.joinpath('electronics', pcb_project,
                                         '3dOut', this_stepfile_name)
baseboard = tb.u.import_step(this_stepfile)
baseboard = baseboard.rotate((0, 0, 0), (0, 0, 1), 180)
baseboard = baseboard.translate((base_l/2, base_w/2, -tb.c.pcb_thickness))
assembly.extend(baseboard.vals())

# position the crossbars
crossbar = crossbar.translate((0, 0, -tb.c.pcb_thickness/2))
crossbar = crossbar.rotate((0, 0, 0), (1, 0, 0), 90)
crossbar = crossbar.translate((0, 0, base_t+crossbar_pcb_top_height))
crossbar = crossbar.translate((base_l/2, 0, 0))
crossbar = crossbar.translate((0, base_w/2-adapter_width/2, 0))
assembly.extend(crossbar.vals())
assembly.extend(crossbar.translate((0, adapter_width, 0)).vals())

# position the adapters
adapter_surface_height = crossbar_pcb_top_height + base_t
adapter = adapter.rotate((0, 0, 0), (0, 0, 1), 90)
adapter = adapter.translate((base_l/2, base_w/2, adapter_surface_height))

assembly.extend(adapter.vals())
assembly.extend(adapter.translate((adapter_spacing, 0, 0)).vals())
assembly.extend(adapter.translate((-adapter_spacing, 0, 0)).vals())

# build an endblock
block = tb.endblock.build(adapter_width=adapter_width, horzm3s=False, pfdowel=True)

# position the block
block = block.translate((tb.endblock.length/2+block_offset_from_edge_of_base, base_w/2, tb.endblock.height/2+base_t))

assembly.extend(block.vals())
assembly.extend(block.mirror('ZY', (base_l/2, 0, 0)).vals())

# build the sandwich
s = sandwich.Sandwich(tb, leng=base_l, wid=base_w, substrate_xy_nominal=adapter_dim, cutout_spacing=adapter_spacing, endblock_width=tb.endblock.length, aux_hole_spacing=tb.endblock.aux_hole_spacing, block_offset_from_edge_of_base=block_offset_from_edge_of_base)
holder = s.build()
holder = holder.translate((base_l/2, base_w/2, tb.endblock.height+base_t))
assembly.extend(holder.Solids())

# drill mounting holes in base
block_mount_hole_center_offset_from_edge = block_offset_from_edge_of_base + tb.endblock.length/2
block_mount_hole_x = base_l/2-block_mount_hole_center_offset_from_edge
# cbore holes for use with RS flangenut Stock No. 725-9650
base = base.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(block_mount_hole_x, 0).cboreHole(2*tb.c.std_screw_threads["m5"]["close_r"], cboreDiameter=tb.c.cbore_dia, cboreDepth=tb.c.cbore_depth, clean=True)
base = base.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(-block_mount_hole_x, 0).cboreHole(2*tb.c.std_screw_threads["m5"]["close_r"], cboreDiameter=tb.c.cbore_dia, cboreDepth=tb.c.cbore_depth, clean=True)

# chamfer the bottom edges
base = base.faces("<Z").edges().chamfer(chamfer_l)

# cut the passthroughs
cq.Workplane.passthrough = tb.passthrough.make_cut
bot_face = base.faces("<Z").workplane(centerOption='CenterOfBoundBox')
bot_face = bot_face.rarray(pcb_tab_spacing, adapter_dim, 2, 2)
base = bot_face.passthrough(rows=8, angle=90, kind="C")

# chamfer the top edges
base = base.faces(">Z").edges().chamfer(chamfer_l)


assembly.extend(base.vals())

this_stepfile = tb.u.wd.joinpath("chamber.stp")
chamber_corner_offset = cq.Vector((107.267, 133.891, 137.882))
assembly_corner_offset = cq.Vector((16, 16.5+1.6, 75))
chamber = tb.u.import_step(this_stepfile)
chamber = chamber.translate(chamber_corner_offset)
chamber = chamber.rotate((0,0,0),(1,0,0), 90)
chamber = chamber.translate((-16, 75, -16.5-1.6))

assembly.extend(chamber.vals())
#show_object(chamber)

# make a compound out of the assembly
cpnd = cq.Compound.makeCompound(assembly)

# export everything (this can take a while)
tb.u.export_step(cpnd, tb.u.wd.joinpath('assembly.step'))

if have_so:
    for thing in assembly:
        show_object(thing)  # type: ignore[name-defined] # noqa: F821
logger.info("Done!")
