#!/usr/bin/env python3
import cadquery
from cadquery import CQ, cq
import geometrics.toolbox as tb
import logging
import pathlib

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
  silicone_t = 0.5  # nominal silicone thickness
  compressed_silicone_fraction = 0.9
  silicone_working_t = silicone_t * compressed_silicone_fraction  # working silicone thickness
  pcb_thickness = 1.6
  pin_working_height = 1.6  # above top pcb surface
  cu_tower_h = pcb_spacer_h + pcb_thickness + pin_working_height - silicone_working_t
  slots_t = cu_tower_h + silicone_working_t + glass_t - (pcb_spacer_h + pcb_thickness)

  cu_nub_h = pcb_spacer_h + pcb_thickness

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

  dxf_filepath = pathlib.Path("2d.dxf")
  pcb_step_filepath = pathlib.Path("pcb.step")
  vent_screw_filepath = pathlib.Path("vent_screw.step")

  def __init__(self):
    if not self.dxf_filepath.exists():
      # probably running from the top of the repo in debug mode...
      self.dxf_filepath = pathlib.Path.cwd()/'badger'/self.dxf_filepath
      self.pcb_step_filepath = pathlib.Path.cwd()/'badger'/self.pcb_step_filepath
      self.vent_screw_filepath = pathlib.Path.cwd()/'badger'/self.vent_screw_filepath

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
      "cu_nubs",
      "cu_base",
      "cu_dowel_pf",
      "cu_towers",
      "Defpoints",
      "dowels",
      "glass",
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
  
  def make_reservation(self):
    vss = self.get_ventscrews_a()
    sr = CQ().box(self.reserve_xy,self.reserve_xy,self.reserve_h,centered=(True,True,False))
    sr = sr.translate((0,0,-self.pcb_thickness-self.pcb_spacer_h-self.cu_base_t))
    wires = CQ().box(self.wire_slot_depth, 2.54*20, 2.54*2, centered=(False, True, False)).translate((-self.reserve_xy/2,0,self.wire_slot_z+self.pcb_thickness/2))
    wiresA = wires.translate((0, self.wire_slot_offset,0))
    wiresB = wires.translate((0,-self.wire_slot_offset,0))
    sr = sr.cut(wiresA).cut(wiresB).add(vss)
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
    spacer = spacer.translate((0, 0, -self.pcb_thickness/2-self.pcb_spacer_h))  # so that we don't have to move the PCB
    return (spacer)
  
  def get_pcb(self):
    pcb = self.pcb
    return pcb.translate((0,0,-self.pcb_thickness/2))

  def make_pusher_plate(self):
    pusher = CQ().add(self.pusher_plate).toPending().extrude(self.pusher_t)
    pusher = pusher.add(self.plate_mounts).toPending().cutThruAll()
    pusher = pusher.translate((0,0,self.pcb_thickness/2+self.slots_t))
    return pusher

  def make_slot_plate(self):
    slots = CQ().add(self.slot_plate).toPending().extrude(self.slots_t)
    slots = slots.add(self.plate_mounts).toPending().cutThruAll()
    slots = slots.translate((0,0,self.pcb_thickness/2))
    return (slots)

  def build(self):
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

    # the vent screws
    vss_a = self.get_ventscrews_a()
    vss_b = self.get_ventscrews_b()
    asy.add(vss_a.add(vss_b), name="ventscrew")

    # the alignment slot plate
    slots = self.make_slot_plate()
    asy.add(slots, name="sample_slots", color=cadquery.Color("GRAY45"))

    pusher = self.make_pusher_plate()
    asy.add(pusher, name="pusher", color=cadquery.Color("GRAY28"))

    reserve = self.make_reservation()
    asy.add(reserve, name="space_reservation")


    return asy


def main():
  s = Badger()
  asy = s.build()
  
  if "show_object" in globals():
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

  elif __name__ == "__main__":
    # save step
    asy.save('badger.step')

    # save STLs
    for key, val in asy.traverse():
      shapes = val.shapes
      if shapes != []:
        c = cq.Compound.makeCompound(shapes)
        cadquery.exporters.export(c.locate(val.loc), f'{val.name}.stl')
        cadquery.exporters.export(c.locate(val.loc), f'{val.name}.step')

main()