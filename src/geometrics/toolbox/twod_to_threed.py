import cadquery
import OCP
from cadquery import CQ, cq
from pathlib import Path
from typing import List, Dict, Tuple, Callable
import ezdxf.filemanagement
from ezdxf.addons.drawing import matplotlib
import concurrent.futures
from geometrics.toolbox.cq_serialize import register as register_cq_helper
import math
import shutil
import subprocess
import zipfile


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
                    stack_done, vcuts, bwire, twire, recess, instruction_copy = future.result()
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
                            asy.add(layer["geometry"], name=layer["name"], color=cadquery.Color(layer["color"]))
                        stacks[stack_done["name"]] = {"assembly": asy, "vcuts": vcuts, "bwire": bwire, "twire": twire, "recess": recess, "instructions": instruction_copy}
                        # stacks.append(stack_done)
                        # key, val = stack_done
                        # stacks[key] = val

        return stacks
        # asy.save(str(Path(__file__).parent / "output" / f"{stack_instructions['name']}.step"))
        # cq.Shape.exportBrep(cq.Compound.makeCompound(itertools.chain.from_iterable([x[1].shapes for x in asy.traverse()])), str(Path(__file__).parent / "output" / "badger.brep"))

    def do_stack(self, instructions, layers) -> Tuple[Dict, List, List, List, List, Dict]:
        # asy = cadquery.Assembly()
        stack = {}
        vcut_faces = []
        b_wire_faces = []
        t_wire_faces = []
        recess_faces = []

        # asy = None
        stack["name"] = instructions["name"]
        if "xyscale" in instructions:
            stack["dxf_scale"] = instructions["xyscale"]
        else:
            stack["dxf_scale"] = 0
        stack["layers"] = []
        # asy.name = instructions["name"]
        z_base = 0
        for stack_layer in instructions["layers"]:
            fuse_faces = []
            make_faces = False
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
            if t:
                twod_faces = []
                for fc in layers[boundary_layer_name]:
                    if stack["dxf_scale"]:
                        fc = fc.scale(stack["dxf_scale"])
                    sld = CQ(fc).wires().toPending().extrude(t).findSolid()
                    if sld:
                        wp = wp.union(sld)
            else:  # 2d case
                twod_faces = layers[boundary_layer_name]
                if stack["dxf_scale"]:
                    for i, fc in enumerate(twod_faces):
                        twod_faces[i] = fc.scale(stack["dxf_scale"])

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
                        given_angle = float(ldln[1])
                        if isinstance(drawing_layer_name, tuple) and (not given_angle):
                            make_faces = True
                        angle = float(ldln[1])

                    for fc in layers[ldln[0]]:
                        if stack["dxf_scale"]:
                            fc = fc.scale(stack["dxf_scale"])
                        if make_faces:
                            fuse_faces.append(fc)  # these faces will be fused to the solid
                        else:  # we're not fusing faces to the solid
                            if t:  # don't do 2d stuff here
                                sld = cadquery.Solid.extrudeLinear(fc, cadquery.Vector(0, 0, t))
                                if loft:
                                    bf = fc.moved(cadquery.Location((0, 0, dent_size)))
                                    tf = layers[ldln[1]][0].moved(cadquery.Location((0, 0, t + dent_size)))
                                    if stack["dxf_scale"]:
                                        tf = tf.scale(stack["dxf_scale"])
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
                            else:
                                twod_faces.append(fc)
                                # print(f'Discarding {drawing_layer_name} in {stack_layer["name"]} in {stack["name"]}: 2D faces can only be defined by one drawing layer')
                if t:
                    if dent_size:
                        dent_layer = stack_layer["edm_dent"]
                        if layers[dent_layer]:
                            recess_faces.append(dent_size)
                            for fc in layers[dent_layer]:
                                if stack["dxf_scale"]:
                                    fc = fc.scale(stack["dxf_scale"])
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
                                    if stack["dxf_scale"]:
                                        dface = dface.scale(stack["dxf_scale"])
                                    recess_faces.append(dface.located(cadquery.Location(point)))

                    mncmpd = cadquery.Compound.makeCompound(moved_negs).mirror("XY", (0, 0, t / 2))
                    mnldmpd = cadquery.Compound.makeCompound(loft_angle_plus_negs_moved).mirror("XY", (0, 0, t / 2))
                    wp = wp.cut(mncmpd)  # this just cuts the straights

                    if "edge_case" in stack_layer:
                        bdfaces = layers[boundary_layer_name]
                        if stack["dxf_scale"]:
                            for i, fc in enumerate(bdfaces):
                                bdfaces[i] = fc.scale(stack["dxf_scale"])
                        bdface_cmpd = cadquery.Compound.makeCompound(bdfaces)
                        edg = CQ().sketch().face(bdface_cmpd)
                        edfaces = layers[stack_layer["edge_case"]]
                        if stack["dxf_scale"]:
                            for i, fc in enumerate(edfaces):
                                edfaces[i] = fc.scale(stack["dxf_scale"])
                        edgc_cmpd = cadquery.Compound.makeCompound(edfaces)
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
                        wp = edg.union(wp)
                        # wp = wp.union(edg, tol=0.0001)
                        # to_fuse = edg.solids().vals() + wp.solids().vals()
                        # edg_fuse = to_fuse.pop().fuse(*to_fuse, glue=True).clean()
                        # wp = CQ(edg_fuse)

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

            if twod_faces:
                print(f"{boundary_layer_name} is 2d")
                if fuse_faces:
                    geometry = cadquery.Compound.makeCompound(twod_faces + fuse_faces)
                else:
                    geometry = cadquery.Compound.makeCompound(twod_faces)
                geometry = geometry.moved(cadquery.Location((0, 0, z_base)))
            else:
                new = wp.translate((0, 0, z_base))
                sld_prt = new.findSolid().Solids()[0]
                if fuse_faces:
                    faces_list = sld_prt.Faces()
                    bottom_face = sld_prt.faces("<Z")
                    ibot = faces_list.index(bottom_face)
                    faces_list.remove(bottom_face)
                    for ff in fuse_faces:
                        bottom_face = bottom_face.fuse(ff)
                    faces_list.insert(ibot, bottom_face)
                    shell = cadquery.Shell.makeShell(faces_list)
                    geometry = cadquery.Solid.makeSolid(shell)
                else:
                    geometry = sld_prt

            new_layer = {"name": stack_layer["name"], "color": stack_layer["color"], "geometry": geometry}
            stack["layers"].append(new_layer)
            # asy.add(new, name=stack_layer["name"], color=cadquery.Color(stack_layer["color"]))
            z_base = z_base + t
        # return (instructions["name"], asy)
        return stack, vcut_faces, b_wire_faces, t_wire_faces, recess_faces, instructions

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

    @staticmethod
    def ensmall(filename: str):
        # attempt to stepreduce it
        cmd = "stepreduce"
        try:
            rslt = subprocess.run([cmd, filename, filename], stdout=subprocess.PIPE)
            print(rslt.stdout.decode())
        except Exception as e:
            rslt = None
            print(f"External call(s) failed to run: f{e}")

        # compress it
        with zipfile.ZipFile(filename.replace(".step", ".stpZ"), mode="w", compression=zipfile.ZIP_DEFLATED) as myzip:
            myzip.write(filename)

    @classmethod
    def outputter(
        cls,
        built: dict[str, dict[str, cadquery.Assembly]],
        wrk_dir: Path,
        save_dxfs=False,
        save_svgs=False,
        save_pdfs=False,
        save_stls=False,
        save_steps=False,
        save_breps=False,
        save_vrmls=False,
        edm_outputs=False,
        nparallel=1,
        show_object: Callable | None = None,
    ):
        """do output tasks on a dictionary of assemblies"""
        for stack_name, result in built.items():
            if ("instructions" in result) and ("sim_mode" in result["instructions"]):
                simulation_outputs = result["instructions"]["sim_mode"]
            else:
                simulation_outputs = False

            if ("instructions" in result) and ("final_scale" in result["instructions"]):
                final_scale = result["instructions"]["final_scale"]
            else:
                final_scale = 0

            # do some cutting for the simulations
            if simulation_outputs:
                # collect the cutting tools
                cutters = []
                for key, val in result["assembly"].traverse():
                    if "cutter" in key:
                        for cutter in val.shapes:
                            cutters.append(cutter)

                for key, val in result["assembly"].traverse():
                    if not val.children:
                        for cutter in cutters:
                            val.obj = val.obj.cut(cutter)

            if final_scale:
                for key, val in result["assembly"].traverse():
                    if not val.children:
                        val.obj = val.obj.scale(final_scale)

            if show_object:  # we're in cq-editor
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
                if simulation_outputs:
                    step_mode = "default"  # "fused" makes the volumes difficult to split in the simulation
                else:
                    step_mode = "default"
                result["assembly"].save(stepfile, mode=step_mode)
                TwoDToThreeD.ensmall(stepfile)

                # result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.brep"))
                result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.xml"), "XML")
                # result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.vtkjs"), "VTKJS")
                result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.glb"), "GLTF")
                result["assembly"].save(str(wrk_dir / "output" / f"{stack_name}.stl"), "STL")
                if not simulation_outputs:
                    if edm_outputs:
                        edm_subdir = f"{stack_name}_edm"
                        Path.mkdir(wrk_dir / "output" / edm_subdir, exist_ok=True)
                        shutil.copy(stepfile, str(wrk_dir / "output" / edm_subdir / f"expected_result_shape.step"))
                        if "vcuts" in result and result["vcuts"]:
                            cadquery.exporters.export(CQ().add(result["vcuts"]), str(wrk_dir / "output" / edm_subdir / f"vertical_wire_paths.dxf"))
                        if "twire" in result and result["twire"]:
                            t_wire_faces = result["twire"]
                            first_face = t_wire_faces[0]
                            ffbb = first_face.BoundingBox()
                            h = round(ffbb.zmax, 6)
                            cadquery.exporters.export(CQ().add(t_wire_faces), str(wrk_dir / "output" / edm_subdir / f"angled_wire_paths_z={h}mm.dxf"))
                        if "bwire" in result and result["bwire"]:
                            b_wire_faces = result["bwire"]
                            first_face = b_wire_faces[0]
                            ffbb = first_face.BoundingBox()
                            h = round(ffbb.zmin, 6)
                            cadquery.exporters.export(CQ().add(b_wire_faces), str(wrk_dir / "output" / edm_subdir / f"angled_wire_paths_z={h}mm.dxf"))
                        if "recess" in result and result["recess"]:
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
                            if c.Volume() or c.Area():  # don't output things that aren't there
                                if save_stls == True:
                                    cadquery.exporters.export(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.stl"), cadquery.exporters.ExportTypes.STL)
                                if save_steps == True:
                                    stepfile = str(wrk_dir / "output" / f"{stack_name}-{val.name}.step")
                                    cadquery.exporters.export(c.locate(val.loc), stepfile, cadquery.exporters.ExportTypes.STEP)
                                    TwoDToThreeD.ensmall(stepfile)
                                if save_breps == True:
                                    cadquery.Shape.exportBrep(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.brep"))
                                if save_vrmls == True:
                                    cadquery.exporters.export(c.locate(val.loc), str(wrk_dir / "output" / f"{stack_name}-{val.name}.wrl"), cadquery.exporters.ExportTypes.VRML)
                                if save_dxfs or save_pdfs or save_svgs:
                                    cl = c.locate(val.loc)
                                    bb = cl.BoundingBox()
                                    #zmid = (bb.zmin + bb.zmax) / 2
                                    #nwp = CQ("XY", origin=(0, 0, zmid)).add(cl)
                                    #dxface = nwp.section()
                                    cut_length = 0
                                    prime_shape = shapes[0]
                                    prime_faces = prime_shape.Faces()
                                    zs = [pf.CenterOfBoundBox().z for pf in prime_faces]
                                    max_face = prime_faces[zs.index(max(zs))]  # TODO: there could be multiple faces at z max
                                    dxwires = max_face.Wires()
                                    for dxwire in dxwires:
                                        cut_length += dxwire.Length()
                                    outdxf_filepath = wrk_dir / "output" / f"{stack_name}-{val.name}-c{cut_length:.1f}-x{bb.xlen:.1f}-y{bb.ylen:.1f}-z{bb.zlen:.2f}.dxf"
                                    if save_dxfs:
                                        cadquery.exporters.export(CQ(max_face), str(outdxf_filepath), cadquery.exporters.ExportTypes.DXF)
                                    if save_svgs:
                                        cadquery.exporters.export(CQ(max_face), str(wrk_dir / "output" / f"{stack_name}-{val.name}.svg"), cadquery.exporters.ExportTypes.SVG)
                                    if save_pdfs:
                                        dxf_file = ezdxf.filemanagement.readfile(outdxf_filepath)
                                        if not save_dxfs:
                                            outdxf_filepath.unlink()
                                        matplotlib.qsave(dxf_file.modelspace(), str(outdxf_filepath) + ".pdf")
