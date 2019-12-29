#!/usr/bin/env python

# NOTE: The toolbox module's folder must be found on your PYTHONPATH
# or in a parent firectory of an item in your PYTHONPATH.
# File loads are done relative to the toolbox module's folder.
# File saves are made into the working directory.
# The working directory is set to be a directory on your PYTHONPATH
# containing this file. Failing that, it becomes pathlib.Path.cwd()

import cadquery as cq  # type: ignore[import]

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


# Use distance between extreme verticies of an object to
# find its length along a coordinate direction
# along can be "X", "Y" or "Z"
def find_length(thisthing, along="X"):
    length = None
    if along == "X":
        length = thisthing.vertices(">X").val().Center().x - \
                 thisthing.vertices("<X").val().Center().x
    elif along == "Y":
        length = thisthing.vertices(">Y").val().Center().y - \
                 thisthing.vertices("<Y").val().Center().y
    elif along == "Z":
        length = thisthing.vertices(">Z").val().Center().z - \
                 thisthing.vertices("<Z").val().Center().z
    return length


# a list for holding all the things
assembly = []  # type: ignore[var-annotated] # noqa: F821


# build an endblock
block = endblock()

#block = block.translate((block_length/2+1,passthrough_w/2,block_height/2+passthrough_t))
#block2 = block.mirror('ZY',(passthrough_l/2,0,0))


#show_object(assembly)

#show_object(block2)

#assembly.add(block)
#
#

holder_step_file = pathlib.PurePath(pathlib.Path(this_file).parent.parent,'otter','cad','ref','otter_substrate_holder.step')
#print(os.__file__)
#holder_step_file = "../../otter/cad/ref/otter_substrate_holder.step"
#holder_step_file = ".."+os.path.sep+".."+os.path.sep+"otter"+os.path.sep+"cad"+os.path.sep+"ref"+os.path.sep+"otter_substrate_holder.step"
#chamber_corner_offset = (107.267, 133.891, 137.882)
holder = cq.importers.importStep(str(holder_step_file))
spacer_thickness = 0 # this is the spacer between their lid and ours
holder = holder.translate((0,-spacer_thickness,0))
#chamber = chamber.translate(chamber_corner_offset)
show_object(holder)



window_support_step_file = "../../environment_chamber/build/support.step"
base_step_file = "../../environment_chamber/build/base.step"
#base_length = 238.02
base_width=201.2
chamber_y_offset=32.624-28.85 # 32.624-28.85=3.774
#chamber_y_offset=0
lid_step_file = "../../environment_chamber/build/lid.step"

# this puts environmental chamber design output into otter holder's step file coordinate system
def to_holder(obj):
    obj = obj.rotate((0,0,0),(1,0,0), -90).rotate((0,0,0),(0,1,0), 90)
    obj = obj.translate((0,chamber_y_offset,0))
    return obj

fourXspacing = 35
fiveXspacing = 29
#position blocks
blocks_offset_from_middle = block_length/2+141.4/2+1
block = block.rotate((0,0,0),(1,0,0), -90).rotate((0,0,0),(0,1,0), 90).translate((0,chamber_y_offset+block_height/2,blocks_offset_from_middle))
blockA = block.translate((3*fourXspacing/2,0,0))
blockB = block.translate((1*fourXspacing/2,0,0))
blockC = block.translate((-1*fourXspacing/2,0,0))
blockD = block.translate((-3*fourXspacing/2,0,0))
blocks = blockA.add(blockB).add(blockC).add(blockD).add(blockA.mirror('XY',(0,0,0))).add(blockB.mirror('XY',(0,0,0))).add(blockC.mirror('XY',(0,0,0))).add(blockD.mirror('XY',(0,0,0)))
blocks.add(blockA.mirror('XY',(0,0,0)))
#blocks.add(block.mirror('XY',(0,0,0)))

#block2 = block.mirror('XY',(0,0,0))
show_object(blocks)
with open("blocks.step", "w") as fh:
    cq.exporters.exportShape(blocks, cq.exporters.ExportTypes.STEP , fh)
#show_object(block2)

ws = cq.importers.importStep(window_support_step_file)
base = cq.importers.importStep(base_step_file)
lid = cq.importers.importStep(lid_step_file)
#ws = ws.rotate((0,0,0),(1,0,0), -90)
show_object(to_holder(ws))
show_object(to_holder(base))
show_object(to_holder(lid))

with open("lid.step", "w") as fh:
    cq.exporters.exportShape(to_holder(lid), cq.exporters.ExportTypes.STEP , fh)

with open("ws.step", "w") as fh:
    cq.exporters.exportShape(to_holder(ws), cq.exporters.ExportTypes.STEP , fh)
    
with open("base.step", "w") as fh:
    cq.exporters.exportShape(to_holder(base), cq.exporters.ExportTypes.STEP , fh)


pcb_project = "otter_substrate_adapter"
adapter_step_file_name = f"../../electronics/{pcb_project}/3dOut/substrate_adapter.step"
adapter = cq.importers.importStep(adapter_step_file_name)
adapter_y_offset =5.97 + 11.43+0.24+chamber_y_offset+1.6

adapter = adapter.rotate((0,0,0),(1,0,0), -90)
adapterA = adapter.translate((3*fourXspacing/2,adapter_y_offset,0))
adapterB = adapter.translate((1*fourXspacing/2,adapter_y_offset,0))
adapterC = adapter.translate((-1*fourXspacing/2,adapter_y_offset,0))
adapterD = adapter.translate((-3*fourXspacing/2,adapter_y_offset,0))

adapterE = adapter.translate((3*fourXspacing/2,adapter_y_offset,fiveXspacing))
adapterF = adapter.translate((1*fourXspacing/2,adapter_y_offset,fiveXspacing))
adapterG = adapter.translate((-1*fourXspacing/2,adapter_y_offset,fiveXspacing))
adapterH = adapter.translate((-3*fourXspacing/2,adapter_y_offset,fiveXspacing))

adapterI = adapter.translate((3*fourXspacing/2,adapter_y_offset,2*fiveXspacing))
adapterJ = adapter.translate((1*fourXspacing/2,adapter_y_offset,2*fiveXspacing))
adapterK = adapter.translate((-1*fourXspacing/2,adapter_y_offset,2*fiveXspacing))
adapterL = adapter.translate((-3*fourXspacing/2,adapter_y_offset,2*fiveXspacing))

adapterM = adapter.translate((3*fourXspacing/2,adapter_y_offset,-1*fiveXspacing))
adapterN = adapter.translate((1*fourXspacing/2,adapter_y_offset,-1*fiveXspacing))
adapterO = adapter.translate((-1*fourXspacing/2,adapter_y_offset,-1*fiveXspacing))
adapterP = adapter.translate((-3*fourXspacing/2,adapter_y_offset,-1*fiveXspacing))

adapterQ = adapter.translate((3*fourXspacing/2,adapter_y_offset,-2*fiveXspacing))
adapterR = adapter.translate((1*fourXspacing/2,adapter_y_offset,-2*fiveXspacing))
adapterS = adapter.translate((-1*fourXspacing/2,adapter_y_offset,-2*fiveXspacing))
adapterT = adapter.translate((-3*fourXspacing/2,adapter_y_offset,-2*fiveXspacing))
adapters = adapterA.add(adapterB).add(adapterC).add(adapterD).add(adapterE).add(adapterF).add(adapterG).add(adapterH).add(adapterI).add(adapterJ).add(adapterK).add(adapterL).add(adapterM).add(adapterN).add(adapterO).add(adapterP).add(adapterQ).add(adapterR).add(adapterS).add(adapterT)
show_object(adapters)
with open("adapterA.step", "w") as fh:
    cq.exporters.exportShape(adapterA, cq.exporters.ExportTypes.STEP , fh)
#with open("T.step", "w") as fh:
#    cq.exporters.exportShape(adapterT, cq.exporters.ExportTypes.STEP , fh)

#with open("L.step", "w") as fh:
#    cq.exporters.exportShape(adapterT, cq.exporters.ExportTypes.STEP , fh)



#assembly.add(adapter)
#assembly.add(adapter.translate((42.5,0,0)))
#assembly.add(adapter.translate((85,0,0)))
#
#assembly = assembly.rotate((0,0,0),(1,0,0), -90)
#assembly = assembly.translate((16, 16.5+1.6,75))
#show_object(assembly)

pcb_project = "otter_crossbar"
crossbar_step_file_name = f"../../electronics/{pcb_project}/3dOut/{pcb_project}.step"
crossbar = cq.importers.importStep(crossbar_step_file_name)
crossbar = crossbar.translate((0,0,-1.6/2))
crossbar = crossbar.rotate((0,0,0),(0,1,0), 90)
crossbar = crossbar.translate((0,11.43+0.24+chamber_y_offset,0))
crossbarA = crossbar.translate((-fourXspacing/2+adapter_width/2,0,0))
crossbarB = crossbar.translate((-fourXspacing/2-adapter_width/2,0,0))

crossbarC = crossbar.translate((-3*fourXspacing/2+adapter_width/2,0,0))
crossbarD = crossbar.translate((-3*fourXspacing/2-adapter_width/2,0,0))

crossbarE = crossbar.translate((fourXspacing/2+adapter_width/2,0,0))
crossbarF = crossbar.translate((fourXspacing/2-adapter_width/2,0,0))

crossbarG = crossbar.translate((3*fourXspacing/2+adapter_width/2,0,0))
crossbarH = crossbar.translate((3*fourXspacing/2-adapter_width/2,0,0))
#assembly = crossbar.translate((0,10,0))
#assembly.add(crossbar.translate((0,40,0)))


#show_object(crossbarB)

with open("cbh.step", "w") as fh:
    cq.exporters.exportShape(crossbarH, cq.exporters.ExportTypes.STEP , fh)

crossbars=crossbarA.add(crossbarB).add(crossbarC).add(crossbarD).add(crossbarE).add(crossbarF).add(crossbarG).add(crossbarH)
#with open("crossbars.step", "w") as fh:
#    cq.exporters.exportShape(crossbars, cq.exporters.ExportTypes.STEP , fh)
show_object(crossbars)
