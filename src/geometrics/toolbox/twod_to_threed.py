import cadquery
from cadquery import CQ, cq
from pathlib import Path
from typing import List, Dict
import ezdxf


class TwoDToThreeD(object):
    sources: List[Path]
    stacks: List[Dict]
    # dxf_filepath = Path(__file__).parent.parent / "oxford" / "master.dxf"  # this makes CQ-editor sad because __file__ is not defined

    def __init__(self, instructions: List[Dict], sources: List[Path]):
        self.stacks: List[Dict] = instructions
        self.sources: List[Path] = sources

    def build(self, stacks_to_build: List[str] = [""]):
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
        self._layers = layers

        stacks = {}
        for stack_instructions in self.stacks:
            asy = cadquery.Assembly()
            # asy = None
            if stack_instructions["name"] in stacks_to_build:
                asy.name = stack_instructions["name"]
                z_base = 0
                for stack_layer in stack_instructions["layers"]:
                    t = stack_layer["thickness"]
                    boundary_layer_name = stack_layer["drawing_layer_names"][0]  # boundary layer must always be the first one listed
                    layer_comp = cadquery.Compound.makeCompound(layers[boundary_layer_name].faces().vals())

                    if "array" in stack_layer:
                        array_points = stack_layer["array"]
                    else:
                        array_points = [(0, 0, 0)]

                    if len(stack_layer["drawing_layer_names"]) == 1:
                        wp = CQ().sketch().push(array_points).face(layer_comp, mode="a", ignore_selection=False)
                    else:
                        wp = CQ().sketch().face(layer_comp, mode="a", ignore_selection=False)

                    wp = wp.finalize().extrude(t)  # the workpiece base is now made
                    if len(stack_layer["drawing_layer_names"]) > 1:
                        wp = wp.faces(">Z").workplane(centerOption="ProjectedOrigin").sketch()

                        for drawing_layer_name in stack_layer["drawing_layer_names"][1:]:
                            layer_comp = cadquery.Compound.makeCompound(layers[drawing_layer_name].faces().vals())
                            wp = wp.push(array_points).face(layer_comp, mode="a", ignore_selection=False)

                        wp = wp.faces()
                        if "edge_case" in stack_layer:
                            edge_layer_name = stack_layer["edge_case"]
                            layer_comp = cadquery.Compound.makeCompound(layers[edge_layer_name].faces().vals())
                            es = CQ().sketch().face(layer_comp)
                            wp = wp.face(es.faces(), mode="i")
                            wp = wp.clean()
                        # wp = wp.finalize().cutThruAll()  # this is a fail, but should work. if it's not a fail is slower than the below line
                        wp = wp.finalize().extrude(-t, combine="cut")

                    # give option to override calculated z_base
                    if "z_base" in stack_layer:
                        z_base = stack_layer["z_base"]

                    new = wp.translate([0, 0, z_base])
                    asy.add(new, name=stack_layer["name"], color=cadquery.Color(stack_layer["color"]))
                    z_base = z_base + t
                stacks[stack_instructions["name"]] = asy
        return stacks
        # asy.save(str(Path(__file__).parent / "output" / f"{stack_instructions['name']}.step"))
        # cq.Shape.exportBrep(cq.Compound.makeCompound(itertools.chain.from_iterable([x[1].shapes for x in asy.traverse()])), str(Path(__file__).parent / "output" / "badger.brep"))

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
            layers[layer_name] = cadquery.importers.importDXF(which_file, exclude=to_exclude)

        return layers

    def faceputter(cls, wrk_dir):
        """ouputs faces that were read from dxfs during build"""
        Path.mkdir(wrk_dir / "output" / "faces", exist_ok=True)
        all_faces = cadquery.Assembly()
        for layer_name, layer_wp in cls._layers.items():
            faces = layer_wp.faces().vals()
            for i, face in enumerate(faces):
                all_faces.add(face)
                cadquery.exporters.export(face, str(wrk_dir / "output" / "faces" / f"{layer_name}-{i}.stl"), cadquery.exporters.ExportTypes.STL)
                cadquery.exporters.export(face, str(wrk_dir / "output" / "faces" / f"{layer_name}-{i}.amf"), cadquery.exporters.ExportTypes.AMF)
                cadquery.exporters.export(face, str(wrk_dir / "output" / "faces" / f"{layer_name}-{i}.wrl"), cadquery.exporters.ExportTypes.VRML)
                cadquery.exporters.export(face, str(wrk_dir / "output" / "faces" / f"{layer_name}-{i}.step"), cadquery.exporters.ExportTypes.STEP)
        all_faces.save(str(wrk_dir / "output" / "faces" / f"all_faces.step"))

    @classmethod
    def outputter(cls, asys, wrk_dir, save_dxfs=False, save_stls=False, save_steps=False, save_breps=False, save_vrmls=False):
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

                # stupid workaround for gltf export bug: https://github.com/CadQuery/cadquery/issues/993
                asy2 = None
                # for path, child in asy._flatten().items():
                for child in asy.children:
                    # if "/" in path:
                    if asy2 is None:
                        asy2 = cadquery.Assembly(child.obj, name=child.name, color=child.color)
                    else:
                        asy2.add(child.obj, name=child.name, color=child.color)
                asy2.save(str(wrk_dir / "output" / f"{stack_name}.glb"), "GLTF")

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
