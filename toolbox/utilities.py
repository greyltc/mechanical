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


def undercutRelief2D(self, length, width, diameter, angle=0, sides=2, corner_tol=0):
    """
    Creates a relief undercut shape for each point on the stack.

    :param diameter: desired diameter of the corner arcs
    :param length: desired end to end length of slot
    :param width: desired width of the slot
    :param angle: angle of slot in degrees, with 0 being along x-axis
    :param sides: can be 1 or 2, giving a 1 or two sided relief shape
    :param corner_tol: how much extra space to give at the corners
    :return: a new CQ object with the created wires on the stack

    Can be used to create arrays of pockets that square cornered things can fit snugly into:

    result = cq.Workplane("XY").box(10,25,3).rarray(1,5,1,5).undercutRelief2D(5,3,1).cutBlind(2)

    """

    def _makeundercut(pnt):
        """
        Inner function that is used to create a relief undercut shape for each point/object on the workplane
        :param pnt: The center point for the slot
        :return: A CQ object representing a relief undercut shape
        """
        error_string = ("undercutRelief2D could not be drawn "
                        "because the relief arcs collide with eachother")

        r = diameter/2

        if sides == 1:
            if width <= diameter:
                raise(ValueError(error_string))
            corner_shift = cq.Vector((0, r, 0))  # TODO: handle corner_tol properly for sides=1
        elif sides == 2:
            along_edge = (r-corner_tol)/(2**(1/2))
            if width <= along_edge*2 or length <= along_edge*2:
                raise(ValueError(error_string))
            corner_shift = cq.Vector((r-along_edge/2, r-along_edge/2, 0))
            # TODO: something about the corner shift with tolerance isn't quite right
        else:
            raise(ValueError("sides must be either 1 or 2"))

        m1_point = cq.Vector((0, width/2, 0))
        m2_point = cq.Vector((length/2, 0, 0))

        c1 = cq.Solid.makeCylinder(r, 1, pnt=cq.Vector(corner_shift))
        c2 = c1.mirror("ZX", m1_point)
        c3 = c2.mirror("YZ", m2_point)
        c4 = c1.mirror("YZ", m2_point)
        b = cq.Solid.makeBox(length, width, 1)

        wp = cq.Workplane("XY")

        shape = wp.union(b).union(c1).union(c2).union(c3).union(c4)
        shape = shape.translate((-length/2, -width/2))
        shape = shape.rotate((0, 0, 0), (0, 0, 1), angle)

        face = shape.faces("<Z").faces().val()
        slot = face.outerWire()
        slot = slot.translate(pnt)

        return slot

    return self.eachpoint(_makeundercut, True)


def set_directories(wd_filename="assemble_system.py"):
    """
    figure out top level directory (tld) and working directory (wd)
    file loads are done relative to tld and saves are done into wd
    """
    global wd, tld

    tld = pathlib.Path(__file__).resolve().parent.parent
    logger.info(f'So the top level directory is "{tld}"')
    # NOTE: I'm sure there's a better way to find wd...
    this_filename = wd_filename
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
