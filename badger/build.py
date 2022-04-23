#!/usr/bin/env python3
import cadquery
from cadquery import CQ, cq
from pathlib import Path
import itertools

class Badger(object):
  cu_base_t = 3
  pcb_spacer_h = 1.6

  reserve_xy = 200
  reserve_h = 20
  wire_slot_depth = 28  # depth from edge
  wire_slot_offset = 46.5  # offset y
  wire_slot_z = 2.095  # offset z
  
  heater_t = 20
  pusher_t = 4

  glass_t = 1.1
  silicone_t = 0.508  # uncompressed silicone thickness (0.02 in https://www.mcmaster.com/86915K22/)
  compressed_silicone_fraction = 0.8  # let's say it'll compress to 0.8 of its initial thickness
  silicone_working_t = silicone_t * compressed_silicone_fraction  # working silicone thickness (just sets up where the glass and the pusher end up in the model)
  pcb_thickness = 1.6
  min_min_height = 0.8  # pins are fully depressed on a surface this far from the PCB
  cu_tower_h = pcb_spacer_h + pcb_thickness + min_min_height  # 0.8 here just ensures the 0921 pins can never bottom out
  # thus the thermal pad material can be any thickness 0 through pin working travel (about 1.4mm, but lets say 1.3mm to be safe)
  slots_t = min_min_height + glass_t

  cu_nub_h = pcb_spacer_h + pcb_thickness - 0.3

  dowel_height = 16

  glass_xy = 25

  screw_depth = 7

  # ventscrew coordinates
  screw_spots = [
    (-93, 93),
    (-31, 93),
    ( 31, 93),
    ( 93, 93),
    ( 93, 31),
    ( 93,-31),
    ( 93,-93),
    ( 31,-93),
    (-31,-93),
    (-93,-93),
    (-93,  0),
  ]

  gs = globals()
  ls = locals()
  print(gs)
  print(ls)
  dxf_filepath = Path(__file__).parent / "drawings" / "2d.dxf"
  pcb_step_filepath = Path(__file__).parent / "components" / "pcb.step"
  vent_screw_filepath = Path(__file__).parent / "components" / "vent_screw.step"

  def __init__(self):
    self.cu_towers = self.get_wires("cu_towers")
    self.base_plate = self.get_wires("base_plate")
    self.cu_base = self.get_wires("cu_base")
    self.plate_mounts = self.get_wires("plate_mounts")
    self.pusher_plate = self.get_wires("pusher_plate")
    self.slot_plate = self.get_wires("slot_plate")
    self.spacer_pcb = self.get_wires("spacer_pcb")
    self.silicone = self.get_wires("silicone")
    self.glass = self.get_wires("glass")
    self.dowels = self.get_wires("dowels")
    self.cu_nubs = self.get_wires("cu_nubs")
    self.cu_dowel_pf = self.get_wires("cu_dowel_pf")
    self.pcb = CQ().add(cadquery.importers.importStep(str(self.pcb_step_filepath)))
    self.vent_screw = CQ().add(cadquery.importers.importStep(str(self.vent_screw_filepath)))
  
  def get_wires (self, layername):
    """returns the wires from the given dxf layer"""
    # list of of all layers in the dxf
    dxf_layernames = [
      "0",
      "base_plate",
      "connector",
      "cu_base",
      "cu_dowel_pf",
      "cu_nubs",
      "cu_towers",
      "Defpoints",
      "dims",
      "dowels",
      "glass",
      "metal_mask",
      "pcb",
      "pin_holes",
      "plate_mounts",
      "pusher_plate",
      "silicone",
      "slot_plate",
      "spacer_pcb",
    ]
    to_exclude = [k for k in dxf_layernames if layername != k]
    dxf_obj = cadquery.importers.importDXF(str(self.dxf_filepath), exclude=to_exclude)
    return(dxf_obj.wires())

  def make_heater_plate(self):
    heater = CQ().add(self.base_plate).toPending().extrude(self.heater_t)
    heater = heater.faces(">Z[-1]").workplane().add(self.plate_mounts).translate((0,0,self.heater_t)).toPending().cutBlind(-self.screw_depth)

    heater = heater.translate((0,0,-self.heater_t-self.cu_base_t-self.pcb_thickness/2-self.pcb_spacer_h))
    return (heater)

  def make_tower_plate(self):
    towers = CQ().add(self.cu_base).toPending().extrude(self.cu_base_t)
    towers = towers.faces("<Z[-2]").workplane().add(self.cu_towers).translate((0,0,self.cu_base_t)).toPending().extrude(self.cu_tower_h)
    towers = towers.faces("<Z[-2]").workplane().add(self.cu_nubs).translate((0,0,self.cu_base_t)).toPending().extrude(self.cu_nub_h)
    towers = towers.add(self.plate_mounts).toPending().cutThruAll()
    towers = towers.add(self.cu_dowel_pf).toPending().cutThruAll()

    towers = towers.translate((0,0,-self.cu_base_t-self.pcb_thickness/2-self.pcb_spacer_h))
    return (towers)

  def get_ventscrews_a(self):
    ventscrew = self.vent_screw.translate((0,0,-1.7))
    ventscrews = CQ().pushPoints(self.screw_spots).eachpoint(lambda loc: ventscrew.val().moved(loc), True)
    return ventscrews

  def get_ventscrews_b(self):
    ventscrew = self.vent_screw.translate((0,0,3.3))
    ventscrews = CQ().pushPoints(self.screw_spots).eachpoint(lambda loc: ventscrew.val().moved(loc), True)
    return ventscrews
  
  def make_reservation(self, do_ventscrews:bool=False):
    if do_ventscrews:
      vss = self.get_ventscrews_a()
    sr = CQ().box(self.reserve_xy,self.reserve_xy,self.reserve_h,centered=(True,True,False))
    sr = sr.translate((0,0,-self.pcb_thickness-self.pcb_spacer_h-self.cu_base_t))
    wires = CQ().box(self.wire_slot_depth, 2.54*20, 2.54*2, centered=(False, True, False)).translate((-self.reserve_xy/2,0,self.wire_slot_z+self.pcb_thickness/2))
    wiresA = wires.translate((0, self.wire_slot_offset,0))
    wiresB = wires.translate((0,-self.wire_slot_offset,0))
    sr = sr.cut(wiresA).cut(wiresB)
    if do_ventscrews:
      sr = sr.add(vss)
    # these next two lines are very expensive (and optional)!
    sr = sr.add(self.get_pcb())
    #sr = CQ().union(sr)
    return sr

  def make_silicone(self):
    silicone = CQ().add(self.silicone).toPending().extrude(self.silicone_t)
    silicone = silicone.translate((0,0,-self.pcb_thickness/2-self.pcb_spacer_h+self.cu_tower_h))
    return silicone

  def make_dowels(self):
    dowels = CQ().add(self.dowels).toPending().extrude(self.dowel_height)
    dowels = dowels.translate((0,0,-self.pcb_thickness/2-self.pcb_spacer_h-self.cu_base_t))
    return dowels

  def make_glass(self):
    glass = CQ().add(self.glass).toPending().extrude(self.glass_t)
    glass = glass.translate((0,0,-self.pcb_thickness/2-self.pcb_spacer_h+self.cu_tower_h+self.silicone_working_t))
    return glass

  def make_spacer_pcb(self):
    spacer = CQ().add(self.spacer_pcb).toPending().extrude(self.pcb_spacer_h)
    spacer = spacer.translate((0, 0, -self.pcb_thickness/2-self.pcb_spacer_h))
    return (spacer)
  
  def get_pcb(self):
    return self.pcb

  def make_pusher_plate(self):
    pusher = CQ().add(self.pusher_plate).toPending().extrude(self.pusher_t)
    pusher = pusher.add(self.plate_mounts).toPending().cutThruAll()
    pusher = pusher.translate((0,0,self.pcb_thickness/2+self.slots_t + self.silicone_working_t))
    return pusher

  def make_slot_plate(self):
    slots = CQ().add(self.slot_plate).toPending().extrude(self.slots_t)
    slots = slots.add(self.plate_mounts).toPending().cutThruAll()
    slots = slots.translate((0,0,self.pcb_thickness/2))
    return (slots)

  def build(self, do_ventscrews:bool=False):
    s = self
    asy = cadquery.Assembly()

    # the spacer PCB
    spacer = s.make_spacer_pcb()
    asy.add(spacer, name="spacer", color=cadquery.Color("DARKGREEN"))

    # the towerplate
    tp = self.make_tower_plate()
    asy.add(tp, name="towers", color=cadquery.Color("GOLDENROD"))

    # dowels
    dwl = self.make_dowels()
    asy.add(dwl, name="dowels", color=cadquery.Color("BLACK"))

    # silicone
    sil = self.make_silicone()
    asy.add(sil, name="silicone", color=cadquery.Color("WHITE"))

    # glass
    glass = self.make_glass()
    asy.add(glass, name="glass", color=cadquery.Color("SKYBLUE"))

    # the heater base plate
    heater = s.make_heater_plate()
    asy.add(heater, name="heater", color=cadquery.Color("MATRAGRAY"))

    # the spring pin PCB
    pcb = self.get_pcb()
    asy.add(pcb, name="pcb", color=cadquery.Color("brown"))

    if do_ventscrews:
      # the vent screws
      vss_a = self.get_ventscrews_a()
      vss_b = self.get_ventscrews_b()
      asy.add(vss_a.add(vss_b), name="ventscrew")

    # the alignment slot plate
    slots = self.make_slot_plate()
    asy.add(slots, name="sample_slots", color=cadquery.Color("GRAY45"))

    pusher = self.make_pusher_plate()
    asy.add(pusher, name="pusher", color=cadquery.Color("GRAY28"))

    reserve = self.make_reservation(do_ventscrews=do_ventscrews)
    asy.add(reserve, name="space_reservation")


    return asy


def main():
  s = Badger()
  asy = s.build(do_ventscrews=False)
  
  if "show_object" in globals():  # we're in cq-editor
    #show_object(asy)
    for key, val in asy.traverse():
      shapes = val.shapes
      if shapes != []:
        c = cq.Compound.makeCompound(shapes)
        odict = {}
        if val.color is not None:
          co = val.color.wrapped.GetRGB()
          rgb = (co.Red(), co.Green(), co.Blue())
          odict['color'] = rgb
        show_object(c.locate(val.loc), name=val.name, options=odict)
  else:
    # save assembly
    asy.save( str(Path(__file__).parent / "output" / 'badger.step'))
    cadquery.exporters.assembly.exportCAF(asy, str(Path(__file__).parent / "output" / 'badger.std'))
    #cq.Shape.exportBrep(cq.Compound.makeCompound(itertools.chain.from_iterable([x[1].shapes for x in asy.traverse()])), str(Path(__file__).parent / 'output' / 'badger.brep'))

    save_indivitual_stls = False
    save_indivitual_steps = True
    save_indivitual_breps = True

    # save STLs
    for key, val in asy.traverse():
      shapes = val.shapes
      if shapes != []:
        c = cq.Compound.makeCompound(shapes)
        if save_indivitual_stls == True:
          cadquery.exporters.export(c.locate(val.loc),  str(Path(__file__).parent / "output" / f'{val.name}.stl'))
        if save_indivitual_steps == True:
          cadquery.exporters.export(c.locate(val.loc), str(Path(__file__).parent / "output" / f'{val.name}.step'))
        if save_indivitual_breps == True:
          cq.Shape.exportBrep(c.locate(val.loc), str(Path(__file__).parent / 'output' / f'{val.name}.brep'))


# temp is what we get when run via cq-editor
if __name__ in ['__main__', 'temp']:
    main()
