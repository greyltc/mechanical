import cadquery
from cadquery import CQ, cq
from pathlib import Path
from typing import List, Dict, Tuple
import ezdxf.filemanagement
import concurrent.futures
from geometrics.toolbox.cq_serialize import register as register_cq_helper
import math
import shutil


class TwoDToThreeD(object):
    sources: List[Path]
    stacks: List[Dict]
    # dxf_filepath = Path(__file__).parent.parent / "oxford" / "master.dxf"  # this makes CQ-editor sad because __file__ is not defined

    def __init__(self, instructions: List[Dict], sources: List[Path]):
        self.stacks: List[Dict] = instructions
        self.sources: List[Path] = sources

    def build(self, stacks_to_build: List[str] = [""], nparallel: int = 1):
        if stacks_to_build == [""]:  # build them all by default
            stacks_to_build = [x["name"] for x in self.stacks]

        drawing_layers_needed = []
        for stack_instructions in self.stacks:
            if stack_instructions["name"] in stacks_to_build:
                for stack_layer in stack_instructions["layers"]:
                    for layer in stack_layer["drawing_layer_names"]:
                        if isinstance(layer, tuple):
                            for subl in layer:
                                if type(subl) is str:
                                    drawing_layers_needed.append(subl)
                        else:
                            drawing_layers_needed.append(layer)
                    if "edge_case" in stack_layer:
                        drawing_layers_needed.append(stack_layer["edge_case"])
                    if "edm_dent" in stack_layer:
                        drawing_layers_needed.append(stack_layer["edm_dent"])
        drawing_layers_needed_unique = list(set(drawing_layers_needed))

        # all the faces we'll need here
        layers = self.get_layers(self.sources, drawing_layers_needed_unique)
        # self._layers = layers

        stacks = {}
        # for stack_instructions in self.stacks:
        #     stack_done = do_stack(stack_instructions)
        #     if stack_done:
        #         key, val = stack_done
        #         stacks[key] = val

        register_cq_helper()  # register picklers

        # filter the build instructions
        build_instructions = []
        for sname in stacks_to_build:
            for instruction in self.stacks:
                if sname == instruction["name"]:
                    build_instructions.append(instruction)

        with concurrent.futures.ProcessPoolExecutor(max_workers=nparallel) as executor:
            fs = [executor.submit(self.do_stack, instruction, layers) for instruction in build_instructions]
            # fs = [executor.submit(self.do_stack, stack_instructions, stacks_to_build, layers) for stack_instructions in self.stacks]
            for future in concurrent.futures.as_completed(fs):
                try:
                    stack_done, vcuts, bwire, twire, recess = future.result()
                except Exception as e:
                    print(repr(e))
                else:
                    if stack_done:
                        asy = cadquery.Assembly()
                        asy.name = stack_done["name"]
                        for layer in stack_done["layers"]:
                            # wp = cq.Workplane()
                            # wp.add(layer["solid"])
                            # asy.add(wp, name=layer["name"], color=cadquery.Color(layer["color"]))
                            asy.add(layer["solid"], name=layer["name"], color=cadquery.Color(layer["color"]))
                        stacks[stack_done["name"]] = {"assembly": asy, "vcuts": vcuts, "bwire": bwire, "twire": twire, "recess": recess}
                        # stacks.append(stack_done)
                        # key, val = stack_done
                        # stacks[key] = val

        return stacks
        # asy.save(str(Path(__file__).parent / "output" / f"{stack_instructions['name']}.step"))
        # cq.Shape.exportBrep(cq.Compound.makeCompound(itertools.chain.from_iterable([x[1].shapes for x in asy.traverse()])), str(Path(__file__).parent / "output" / "badger.brep"))

    def do_stack(self, instructions, layers) -> Tuple[Dict, List, List, List, List]:

        # asy = cadquery.Assembly()
        stack = {}
        vcut_faces = []
        b_wire_faces = []
        t_wire_faces = []
        recess_faces = []

        # asy = None
        stack["name"] = instructions["name"]
        stack["layers"] = []
        # asy.name = instructions["name"]
        z_base = 0

        for stack_layer in instructions["layers"]:
            if ("edm_dent" in stack_layer) and ("edm_dent_depth" in stack_layer):
                dent_size = stack_layer["edm_dent_depth"]
            else:
                dent_size = 0
            t = stack_layer["thickness"]
            boundary_layer_name = stack_layer["drawing_layer_names"][0]  # boundary layer must always be the first one listed

            if "array" in stack_layer:
                array_points = stack_layer["array"]
            else:
                array_points = [(0, 0, 0)]

            wp = CQ()
            for fc in layers[boundary_layer_name]:
                sld = CQ(fc).wires().toPending().extrude(t).findSolid()
                if sld:
                    wp = wp.union(sld)

            if len(stack_layer["drawing_layer_names"]) > 1:
                negs: List[cadquery.Shape] = []
                loft_angle_negs: List[cadquery.Shape] = []  # just the loft shapes
                loft_angle_plus_negs: List[cadquery.Shape] = []  # the loft shapes unioned with their straights
                for i, drawing_layer_name in enumerate(stack_layer["drawing_layer_names"][1:]):
                    loft = False
                    if isinstance(drawing_layer_name, tuple):
                        ldln = (drawing_layer_name[0], drawing_layer_name[1])
                        if type(ldln[1]) is str:
                            loft = True
                    else:
                        ldln = (drawing_layer_name, 0)

                    if loft:
                        angle = 0
                    else:
                        angle = float(ldln[1])

                    for fc in layers[ldln[0]]:
                        sld = cadquery.Solid.extrudeLinear(fc, cadquery.Vector(0, 0, t))
                        if loft:
                            bf = fc.moved(cadquery.Location((0, 0, dent_size)))
                            tf = layers[ldln[1]][0].moved(cadquery.Location((0, 0, t + dent_size)))
                            bw = bf.Wires()[0]
                            tw = tf.Wires()[0]
                            lsld = cadquery.Solid.makeLoft([bw, tw])
                            sld = sld.fuse(lsld).clean()
                            # negs.append(sld)
                            loft_angle_negs.append(lsld)
                            loft_angle_plus_negs.append(sld)
                            break  # loft only supports layers with one face
                        elif angle:
                            alongz = t - dent_size
                            along = alongz / math.cos(math.radians(angle))
                            # these faces can't be polylines...(explode them to make this work!)
                            asld = cadquery.Solid.extrudeLinear(fc.moved(cadquery.Location((0, 0, dent_size))), cadquery.Vector(0, 0, along), angle)
                            sld = sld.fuse(asld).clean()
                            # negs.append(sld)
                            loft_angle_negs.append(asld)
                            loft_angle_plus_negs.append(sld)
                        else:
                            negs.append(sld)

                if dent_size:
                    dent_layer = stack_layer["edm_dent"]
                    if layers[dent_layer]:
                        recess_faces.append(dent_size)
                        for fc in layers[dent_layer]:
                            sld = cadquery.Solid.extrudeLinear(fc, cadquery.Vector(0, 0, dent_size))
                            negs.append(sld)

                moved_negs = []
                loft_angle_negs_moved = []
                loft_angle_plus_negs_moved = []

                nofthem = len(negs)
                if nofthem > 1:
                    neg_fuse = negs.pop().fuse(*negs).clean()
                elif nofthem == 1:
                    neg_fuse = negs[0]
                else:
                    neg_fuse = None

                nofthem = len(loft_angle_plus_negs)
                if nofthem > 1:
                    loft_angle_plus_neg_fuse = loft_angle_plus_negs.pop().fuse(*loft_angle_plus_negs).clean()
                elif nofthem == 1:
                    loft_angle_plus_neg_fuse = loft_angle_plus_negs[0]
                else:
                    loft_angle_plus_neg_fuse = None

                # for s in neg_fuse.Solids():  # testing
                #     cadquery.exporters.export(s, f"/tmp/{s}.step")  # testing
                for point in array_points:
                    if neg_fuse:
                        moved_negs.append(neg_fuse.located(cadquery.Location(point)))
                    if loft_angle_plus_neg_fuse:
                        loft_angle_plus_negs_moved.append(loft_angle_plus_neg_fuse.located(cadquery.Location(point)))
                    for loft_angle_neg in loft_angle_negs:
                        loft_angle_negs_moved.append(loft_angle_neg.located(cadquery.Location(point)))
                    if dent_size:
                        if layers[stack_layer["edm_dent"]]:
                            for dface in layers[stack_layer["edm_dent"]]:
                                recess_faces.append(dface.located(cadquery.Location(point)))

                mncmpd = cadquery.Compound.makeCompound(moved_negs)
                mnldmpd = cadquery.Compound.makeCompound(loft_angle_plus_negs_moved)
                wp = wp.cut(mncmpd)  # this just cuts the straights

                if "edge_case" in stack_layer:
                    bdface_cmpd = cadquery.Compound.makeCompound(layers[boundary_layer_name])
                    edg = CQ().sketch().face(bdface_cmpd)
                    edgc_cmpd = cadquery.Compound.makeCompound(layers[stack_layer["edge_case"]])
                    edg = edg.face(edgc_cmpd, mode="s").finalize().extrude(t)
                    edge = True
                else:
                    edgc_cmpd = []
                    edg = CQ()
                    edge = False

                if edge:
                    wp = wp.union(edg)
                vcut_faces = wp.faces(">Z").vals()

                wp = wp.cut(mnldmpd)  # this cuts the lofts and angles
                if edge:
                    wp = wp.union(edg)

                # extract the faces for wire paths
                if loft_angle_negs_moved:
                    wfwp = CQ().add(loft_angle_negs_moved)
                    if "edge_case" in stack_layer:
                        inside_edge = CQ().sketch().face(edgc_cmpd).finalize().extrude(t + dent_size)
                        wfwp = wfwp.intersect(inside_edge)
                    t_wire_faces = wfwp.faces(">Z").vals()
                    b_wire_faces = wfwp.faces("<Z").vals()

            # give option to override calculated z_base
            if "z_base" in stack_layer:
                z_base = stack_layer["z_base"]

            new = wp.translate((0, 0, z_base))
            new_layer = {"name": stack_layer["name"], "color": stack_layer["color"], "solid": new.findSolid()}
            stack["layers"].append(new_layer)
            # asy.add(new, name=stack_layer["name"], color=cadquery.Color(stack_layer["color"]))
            z_base = z_base + t
        # return (instructions["name"], asy)
        return stack, vcut_faces, b_wire_faces, t_wire_faces, recess_faces

    def get_layers(self, dxf_filepaths: List[Path], layer_names: List[str] = []) -> Dict[str, cq.Workplane]:
        """returns the requested layers from dxfs"""
        # list of of all layers in the dxf
        layer_sets = []
        for filepath in dxf_filepaths:
            file_path_str = str(filepath)
            dxf = ezdxf.filemanagement.readfile(file_path_str)
            layer_sets.append(set(dxf.modelspace().groupby(dxfattrib="layer").keys()))

        if len(layer_sets) > 1:
            bad_intersection = set.intersection(*layer_sets)
            if bad_intersection:
                raise ValueError(f"Identical layer names found in multiple drawings: {bad_intersection}")
        layers = {}
        for layer_name in layer_names:
            for i, layer_set in enumerate(layer_sets):
                if layer_name in layer_set:
                    which_file = dxf_filepaths[i]
                    break
            else:
                raise ValueError(f"Could not a layer named '{layer_name}' in any drawing")
            to_exclude = list(layer_set - set((layer_name,)))
            layers[layer_name] = cadquery.importers.importDXF(which_file, exclude=to_exclude).faces().vals()

        return layers

    def faceputter(self, wrk_dir, layers):
        """ouputs faces that were read from dxfs during build"""
        Path.mkdir(wrk_dir / "output" / "faces", exist_ok=True)
        all_faces = cadquery.Assembly()
        for layer_name, faces in layers.items():
            for i, face in enumerate(faces):
                all_faces.add(face)
                cadquery.exporters.export(face, str(wrk_dir / "output" / "faces" / f"{layer_name}-{i}.stl"), cadquery.exporters.ExportTypes.STL)
                cadquery.exporters.export(face, str(wrk_dir / "output" / "faces" / f"{layer_name}-{i}.amf"), cadquery.exporters.ExportTypes.AMF)
                cadquery.exporters.export(face, str(wrk_dir / "output" / "faces" / f"{layer_name}-{i}.wrl"), cadquery.exporters.ExportTypes.VRML)
                cadquery.exporters.export(face, str(wrk_dir / "output" / "faces" / f"{layer_name}-{i}.step"), cadquery.exporters.ExportTypes.STEP)
        all_faces.save(str(wrk_dir / "output" / "faces" / f"all_faces.step"))

    @classmethod
    def outputter(cls, built, wrk_dir, save_dxfs=False, save_stls=False, save_steps=False, save_breps=False, save_vrmls=False, edm_outputs=True, nparallel=1):
        """do output tasks on a dictionary of assemblies"""
        for stack_name, result in built.items():
            if "show_object" in globals():  # we're in cq-editor
                assembly_mode = True  # at the moment, when true we can't select/deselect subassembly parts
                if assembly_mode:
                    show_object(result["assembly"])
                else:
                    for key, val in result["assembly"].traverse():
                        shapes = val.shapes
                        if shapes != []:
                            c = cadquery.Compound.makeCompound(shapes)
                            odict = {}
                            if val.color is not None:
                                co = val.color.wrapped.GetRGB()
                                rgb = (co.Red(), co.Green(), co.Blue())
                                odict["color"] = rgb
                            show_object(c.locate(val.loc), name=val.name, options=odict)
            else:
                Path.mkdir(wrk_dir / "output", exist_ok=True)

                # save assembly
                stepfile = str(wrk_dir / "output" / f"{stack_name}.step")
                result["assembly"].save(stepfile)
                # result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.brep"))
                result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.xml"), "XML")
                # result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.vtkjs"), "VTKJS")
                result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.glb"), "GLTF")
                result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.stl"), "STL")

                if edm_outputs:
                    edm_subdir = f"{stack_name}_edm"
                    Path.mkdir(wrk_dir / "output" / edm_subdir, exist_ok=True)
                    shutil.copy(stepfile, str(wrk_dir / "output" / edm_subdir / f"expected_result_shape.step"))
                    if result["vcuts"]:
                        cadquery.exporters.export(CQ().add(result["vcuts"]), str(wrk_dir / "output" / edm_subdir / f"vertical_wire_paths.dxf"))
                    if result["twire"]:
                        t_wire_faces = result["twire"]
                        first_face = t_wire_faces[0]
                        ffbb = first_face.BoundingBox()
                        h = round(ffbb.zmax, 6)
                        cadquery.exporters.export(CQ().add(t_wire_faces), str(wrk_dir / "output" / edm_subdir / f"angled_wire_paths_z={h}mm.dxf"))
                    if result["bwire"]:
                        b_wire_faces = result["bwire"]
                        first_face = b_wire_faces[0]
                        ffbb = first_face.BoundingBox()
                        h = round(ffbb.zmin, 6)
                        cadquery.exporters.export(CQ().add(b_wire_faces), str(wrk_dir / "output" / edm_subdir / f"angled_wire_paths_z={h}mm.dxf"))
                    if result["recess"]:
                        depth = result["recess"][0]
                        cadquery.exporters.export(CQ().add(result["recess"][1:]), str(wrk_dir / "output" / edm_subdir / f"recess_from_z=0_to_z={depth}mm.dxf"))

                # # stupid workaround for gltf export bug: https://github.com/CadQuery/cadquery/issues/993
                # asy2 = None
                # # for path, child in asy._flatten().items():
                # for child in asy.children:
                #     # if "/" in path:
                #     if asy2 is None:
                #         asy2 = cadquery.Assembly(child.obj, name=child.name, color=child.color)
                #     else:
                #         asy2.add(child.obj, name=child.name, color=child.color)
                # asy2.save(str(wrk_dir / "output" / f"{stack_name}.glb"), "GLTF")

                # cadquery.exporters.assembly.exportCAF(asy, str(wrk_dir / "output" / f"{stack_name}.std"))
                # cq.Shape.exportBrep(cq.Compound.makeCompound(itertools.chain.from_iterable([x[1].shapes for x in asy.traverse()])), str(wrk_dir / "output" / f"{stack_name}.brep"))

                # save each shape individually
                for key, val in result["assembly"].traverse():
                    shapes = val.shapes
                    if shapes != []:
                        c = cadquery.Compound.makeCompound(shapes)
                        if save_stls == True:
                            cadquery.exporters.export(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.stl"), cadquery.exporters.ExportTypes.STL)
                        if save_steps == True:
                            cadquery.exporters.export(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.step"), cadquery.exporters.ExportTypes.STEP)
                        if save_breps == True:
                            cadquery.Shape.exportBrep(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.brep"))
                        if save_vrmls == True:
                            cadquery.exporters.export(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.wrl"), cadquery.exporters.ExportTypes.VRML)
                        if save_dxfs == True:
                            cl = c.locate(val.loc)
                            bb = cl.BoundingBox()
                            zmid = (bb.zmin + bb.zmax) / 2
                            nwp = CQ("XY", origin=(0, 0, zmid)).add(cl)
                            dxface = nwp.section()
                            cadquery.exporters.export(dxface, str(wrk_dir / "output" / f"{stack_name}-{val.name}.dxf"), cadquery.exporters.ExportTypes.DXF)
