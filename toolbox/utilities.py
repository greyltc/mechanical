import sys
import logging
import pathlib  # noqa: F401
import cadquery as cq  # type: ignore[import]

# setup logging
logger = logging.getLogger('cadbuilder')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(('%(asctime)s|%(name)s|%(levelname)s|'
                               '%(message)s'))
ch.setFormatter(formatter)
logger.addHandler(ch)

wd: pathlib.Path = None  # type: ignore[assignment] # noqa: F821
tld: pathlib.Path = None  # type: ignore[assignment] # noqa: F821


def set_directories(wd_filename="assemble_system.py"):
    """
    figure out top level directory (tld) and working directory (wd)
    file loads are done relative to tld and saves are done into wd
    """
    global wd, tld

    tld = pathlib.Path(__file__).resolve().parent.parent
    logger.info(f'So the top level directory is "{tld}"')
    # NOTE: I'm sure there's a better way to find wd...
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


def find_length(thisthing, along="X"):
    """
    Use distance between extreme verticies of an object to
    find its length along a coordinate direction
    along can be "X", "Y" or "Z"
    """
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
