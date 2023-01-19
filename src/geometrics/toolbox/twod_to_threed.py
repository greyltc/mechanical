import cadquery
from cadquery import CQ, cq
from pathlib import Path
from typing import List, Dict
import ezdxf
import concurrent.futures
from geometrics.toolbox.cq_serialize import register as register_cq_helper


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
                    drawing_layers_needed += stack_layer["drawing_layer_names"]
                    if "edge_case" in stack_layer:
                        drawing_layers_needed.append(stack_layer["edge_case"])
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

        with concurrent.futures.ProcessPoolExecutor(max_workers=nparallel) as executor:
            fs = [executor.submit(self.do_stack, stack_instructions, stacks_to_build, layers) for stack_instructions in self.stacks]
            for future in concurrent.futures.as_completed(fs):
                try:
                    stack_done = future.result()
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
                        stacks[stack_done["name"]] = asy
                        # stacks.append(stack_done)
                        # key, val = stack_done
                        # stacks[key] = val

        return stacks
        # asy.save(str(Path(__file__).parent / "output" / f"{stack_instructions['name']}.step"))
        # cq.Shape.exportBrep(cq.Compound.makeCompound(itertools.chain.from_iterable([x[1].shapes for x in asy.traverse()])), str(Path(__file__).parent / "output" / "badger.brep"))

    def do_stack(self, instructions, stacks_to_build, layers):

        # asy = cadquery.Assembly()
        stack = {}
        # asy = None
        if instructions["name"] in stacks_to_build:
            stack["name"] = instructions["name"]
            stack["layers"] = []
            # asy.name = instructions["name"]
            z_base = 0

            for stack_layer in instructions["layers"]:
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
                ext = wp

                if len(stack_layer["drawing_layer_names"]) > 1:
                    subwp = CQ()
                    for drawing_layer_name in stack_layer["drawing_layer_names"][1:]:
                        for point in array_points:
                            for fc in layers[drawing_layer_name]:
                                # if "edm" in drawing_layer_name:
                                if "high_res" in drawing_layer_name:
                                    v = 0.57735  # for 30 deg
                                    trans = 0.2
                                    bar = CQ()
                                    for fc2 in layers[boundary_layer_name]:
                                        sld = CQ(fc2).wires().toPending().extrude(t + trans).findSolid()
                                        if sld:
                                            bar = bar.union(sld)

                                    neg = bar.cut(CQ(fc).wires().toPending().extrude(t + trans).findSolid()).faces(">Z").edges("(not <X) and (not >X) and (not <Y) and (not >Y)").chamfer(v, t)
                                    twp = ext.cut(neg.translate((0, 0, -trans)))
                                    sld = twp.findSolid()
                                else:
                                    sld = CQ(fc.located(cadquery.Location(point))).wires().toPending().extrude(t).findSolid()
                                if sld:
                                    # wp = wp.cut(sld)
                                    subwp = subwp.add(sld)
                                # subos.append(sld)
                    last = subwp.last()
                    if last:
                        subwp = subwp.union(last)
                        wp = wp.cut(subwp)
                    # if subwp.findSolid():
                    #    wp = wp.cut(subwp)
                    #    subocmpd = cadquery.Compound.makeCompound(subos)
                    #    wp = wp.cut(subocmpd)
                    # for subo in subos:

                    if "edge_case" in stack_layer:
                        edge_bits = []
                        for fc in layers[stack_layer["edge_case"]]:
                            sld = CQ(fc).wires().toPending().extrude(t).findSolid()
                            if sld:
                                edge_bits.append(sld)
                        if edge_bits:
                            edgecmpd = cadquery.Compound.makeCompound(edge_bits)
                            edge = ext.cut(edgecmpd)
                            wp = wp.union(edge)

                # give option to override calculated z_base
                if "z_base" in stack_layer:
                    z_base = stack_layer["z_base"]

                new = wp.translate([0, 0, z_base])
                new_layer = {"name": stack_layer["name"], "color": stack_layer["color"], "solid": new.findSolid()}
                stack["layers"].append(new_layer)
                # asy.add(new, name=stack_layer["name"], color=cadquery.Color(stack_layer["color"]))
                z_base = z_base + t
            # return (instructions["name"], asy)
            return stack
        return None

    def get_layers(self, dxf_filepaths: List[Path], layer_names: List[str] = []) -> List[cq.Workplane]:
        """returns the requested layers from dxfs"""
        # list of of all layers in the dxf
        layer_sets = []
        for filepath in dxf_filepaths:
            file_path_str = str(filepath)
            dxf = ezdxf.readfile(file_path_str)
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
    def outputter(cls, asys, wrk_dir, save_dxfs=False, save_stls=False, save_steps=False, save_breps=False, save_vrmls=False, nparallel=1):
        """do output tasks on a dictionary of assemblies"""
        for stack_name, asy in asys.items():
            if "show_object" in globals():  # we're in cq-editor
                assembly_mode = True  # at the moment, when true we can't select/deselect subassembly parts
                if assembly_mode:
                    show_object(asy)
                else:
                    for key, val in asy.traverse():
                        shapes = val.shapes
                        if shapes != []:
                            c = cq.Compound.makeCompound(shapes)
                            odict = {}
                            if val.color is not None:
                                co = val.color.wrapped.GetRGB()
                                rgb = (co.Red(), co.Green(), co.Blue())
                                odict["color"] = rgb
                            show_object(c.locate(val.loc), name=val.name, options=odict)
            else:
                Path.mkdir(wrk_dir / "output", exist_ok=True)

                # save assembly
                asy.save(str(wrk_dir / "output" / f"{stack_name}.step"))
                # asy.save(str(wrk_dir / "output" / f"{stack_name}.brep"))
                asy.save(str(wrk_dir / "output" / f"{stack_name}.xml"), "XML")
                # asy.save(str(wrk_dir / "output" / f"{stack_name}.vtkjs"), "VTKJS")
                asy.save(str(wrk_dir / "output" / f"{stack_name}.glb"), "GLTF")
                asy.save(str(wrk_dir / "output" / f"{stack_name}.stl"), "STL")

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
                for key, val in asy.traverse():
                    shapes = val.shapes
                    if shapes != []:
                        c = cq.Compound.makeCompound(shapes)
                        if save_stls == True:
                            cadquery.exporters.export(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.stl"), cadquery.exporters.ExportTypes.STL)
                        if save_steps == True:
                            cadquery.exporters.export(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.step"), cadquery.exporters.ExportTypes.STEP)
                        if save_breps == True:
                            cq.Shape.exportBrep(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.brep"))
                        if save_vrmls == True:
                            cadquery.exporters.export(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.wrl"), cadquery.exporters.ExportTypes.VRML)
                        if save_dxfs == True:
                            cl = c.locate(val.loc)
                            bb = cl.BoundingBox()
                            zmid = (bb.zmin + bb.zmax) / 2
                            nwp = CQ("XY", origin=(0, 0, zmid)).add(cl)
                            dxface = nwp.section()
                            cadquery.exporters.export(dxface, str(wrk_dir / "output" / f"{stack_name}-{val.name}.dxf"), cadquery.exporters.ExportTypes.DXF)
