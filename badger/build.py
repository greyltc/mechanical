#!/usr/bin/env python3
import cadquery
from cadquery import CQ, cq
import geometrics.toolbox as tb
import logging
import pathlib

class Badger(object):
  cu_base_t = 3
  cu_tower_h = 4.7
  pcb_spacer_h = 1.6
  heater_t = 20
  pusher_t = 4
  slots_t = 3

  screw_depth = 10

  dxf_filepath = pathlib.Path("2d.dxf")
  pcb_step_filepath = pathlib.Path("pcb.step")

  def __init__(self):
    if not self.dxf_filepath.exists():
      # probably running from the top of the repo in debug mode...
      self.dxf_filepath = pathlib.Path.cwd()/'badger'/self.dxf_filepath
    if not self.pcb_step_filepath.exists():
      # probably running from the top of the repo in debug mode...
      self.pcb_step_filepath = pathlib.Path.cwd()/'badger'/self.pcb_step_filepath

    self.cu_towers = self.get_wires("cu_towers")
    self.base_plate = self.get_wires("base_plate")
    self.cu_base = self.get_wires("cu_base")
    self.plate_mounts = self.get_wires("plate_mounts")
    self.pusher_plate = self.get_wires("pusher_plate")
    self.slot_plate = self.get_wires("slot_plate")
    self.spacer_pcb = self.get_wires("spacer_pcb")
    self.pcb = cadquery.importers.importStep(str(self.pcb_step_filepath))
  
  def get_wires (self, layername):
    """returns the wires from the given dxf layer"""
    # list of of all layers in the dxf
    dxf_layernames = [
      "0",
      "Defpoints",
      "base_plate",
      "connector",
      "cu_base",
      "cu_towers",
      "pcb",
      "pin_holes",
      "plate_mounts",
      "pusher_plate",
      "slot_plate",
      "spacer_pcb",
    ]
    to_exclude = [k for k in dxf_layernames if layername != k]
    dxf_obj = cadquery.importers.importDXF(str(self.dxf_filepath), exclude=to_exclude)
    return(dxf_obj.wires())

  def make_heater_plate(self):
    heater = CQ().add(self.base_plate).toPending().extrude(self.heater_t)
    heater = heater.faces(">Z").workplane().add(self.plate_mounts).translate((0,0,self.heater_t)).toPending().cutBlind(-self.screw_depth)

    # tags for assembly
    heater.faces(">Z").tag("top")
    heater.faces(">Z").edges(">Y").tag("top_e")
    heater.faces(">Z").edges("<Y").tag("top_e2")
    return (heater)

  def make_tower_plate(self):
    towers = CQ().add(self.cu_base).toPending().extrude(self.cu_base_t)
    towers = towers.faces(">Z").workplane().add(self.cu_towers).translate((0,0,self.cu_base_t)).toPending().extrude(self.cu_tower_h)
    towers = towers.add(self.plate_mounts).toPending().cutThruAll()

    towers.faces(">Z[-2]").tag("top")
    towers.faces(">Z[-2]").edges(">Y").tag("top_e")
    towers.faces(">Z[-2]").edges("<Y").tag("top_e2")

    towers.faces("<Z").tag("bot")
    towers.faces("<Z").edges(">Y").tag("bot_e")
    towers.faces("<Z").edges("<Y").tag("bot_e2")
    return (towers)

  def make_spacer_pcb(self):
    spacer = CQ().add(self.spacer_pcb).toPending().extrude(self.pcb_spacer_h)
    spacer = spacer.add(self.plate_mounts).toPending().cutThruAll()
    spacer = spacer.translate((0, 0, -1.6/2-self.pcb_spacer_h))  # so that we don't have to move the PCB

    # tags for assembly
    spacer.faces("<Z").tag("bot")
    spacer.faces("<Z").edges(">Y").tag("bot_e")
    spacer.faces("<Z").edges("<Y").tag("bot_e2")
    spacer.faces(">Z").tag("top")
    spacer.faces(">Z").edges(">Y").tag("top_e")
    spacer.faces(">Z").edges("<Y").tag("top_e2")
    return (spacer)
  
  def get_pcb(self):
    pcb = self.pcb

    # tags for assembly
    pcb.faces(">Z[-2]").tag("bot")
    pcb.faces(">Z[-2]").edges(">Y").tag("bot_e")
    pcb.faces(">Z[-2]").edges("<Y").tag("bot_e2")
    pcb.faces(">Z[-1]").tag("top")
    pcb.faces(">Z[-1]").edges(">Y").tag("top_e")
    pcb.faces(">Z[-1]").edges("<Y").tag("top_e2")
    return pcb

  def make_pusher_plate(self):
    pusher = CQ().add(self.pusher_plate).toPending().extrude(self.pusher_t)
    pusher = pusher.add(self.plate_mounts).toPending().cutThruAll()

    # tags for assembly
    pusher.faces("<Z").tag("bot")
    pusher.faces("<Z").edges(">Y").tag("bot_e")
    pusher.faces("<Z").edges("<Y").tag("bot_e2")
    return pusher

  def make_slot_plate(self):
    slots = CQ().add(self.slot_plate).toPending().extrude(self.slots_t)
    slots = slots.add(self.plate_mounts).toPending().cutThruAll()

    # tags for assembly
    slots.faces("<Z").tag("bot")
    slots.faces("<Z").edges(">Y").tag("bot_e")
    slots.faces("<Z").edges("<Y").tag("bot_e2")

    slots.faces(">Z").tag("top")
    slots.faces(">Z").edges(">Y").tag("top_e")
    slots.faces(">Z").edges("<Y").tag("top_e2")

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

    # the heater base plate
    heater = s.make_heater_plate()
    asy.add(heater, name="heater", color=cadquery.Color("MATRAGRAY"))

    # the spring pin PCB
    pcb = self.get_pcb()
    asy.add(pcb, name="pcb", color=cadquery.Color("brown"))

    # the alignment slot plate
    slots = self.make_slot_plate()
    asy.add(slots, name="sample_slots", color=cadquery.Color("GRAY"))

    pusher = self.make_pusher_plate()
    asy.add(pusher, name="pusher", color=cadquery.Color("WHITE"))



    # make the middle piece
    #middle, top_mid= self.make_middle(werkplane)
    #asy.add(middle, name="middle", color=cadquery.Color("orange"))
    #asy.add(top_mid, name="top_mid", color=cadquery.Color("yellow"))

    # make the top piece
    #top = self.make_top(x, y)
    #asy.add(vg, name="vg")

    # constrain assembly

    # towers to spacer PCB
    asy.constrain("spacer?bot", "towers?top", "Axis")
    asy.constrain("spacer?bot_e2", "towers?top_e2", "Point")
    asy.constrain("spacer?bot_e", "towers?top_e", "Point")

    # heater plate to towers PCB
    asy.constrain("towers?bot", "heater?top", "Axis")
    asy.constrain("towers?bot_e2", "heater?top_e2", "Point")
    asy.constrain("towers?bot_e", "heater?top_e", "Point")

    # pcb to spacer PCB
    asy.constrain("spacer?top", "pcb?bot", "Axis")
    asy.constrain("spacer?top_e2", "pcb?bot_e2", "Point")
    asy.constrain("spacer?top_e", "pcb?bot_e", "Point")

    # sample_slots to PCB
    asy.constrain("pcb?top", "sample_slots?bot", "Axis")
    asy.constrain("pcb?top_e2", "sample_slots?bot_e2", "Point")
    asy.constrain("pcb?top_e", "sample_slots?bot_e", "Point")
    
    # pusher to sample_slotsts
    asy.constrain("sample_slots?top", "pusher?bot", "Axis")
    asy.constrain("sample_slots?top_e2", "pusher?bot_e2", "Point")
    asy.constrain("sample_slots?top_e", "pusher?bot_e", "Point")
    

    # solve constraints
    asy.solve()

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

main()