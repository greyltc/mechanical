#!/usr/bin/env python3
import cadquery
from cadquery import CQ, cq
import geometrics.toolbox as tb
import logging
import pathlib


class Badger(object):
  cu_base_t = 3
  cu_tower_h = 3
  pcb_spacer_h = 1.2
  heater_t = 10
  pusher_t = 10

  slots_t = 3
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
    heater = CQ().add(self.base_plate).toPending().extrude(self.cu_tower_h)
    heater.faces("<Z[-1]").tag("top")
    return (heater)

  def make_tower_plate(self):
    towers = CQ().add(self.cu_base).toPending().extrude(self.cu_base_t)
    #towers = towers.faces(">Z[-1]").workplane().circle(30).extrude(1)
    towers = towers.faces(">Z[-1]").workplane().add(self.cu_towers).translate((0,0,self.cu_base_t)).toPending().extrude(self.cu_tower_h)
    return (towers)

  def make_spacer_pcb(self):
    spacer = CQ().add(self.spacer_pcb).toPending().extrude(self.pcb_spacer_h)
    spacer = spacer.translate((0,0,-self.pcb_spacer_h))  # so that we don't have to move the PCB

    spacer.faces(">Z[-1]").tag("bot")
    return (spacer)

  def make_pusher_plate(self):
    pusher = CQ().add(self.pusher_plate).toPending().extrude(self.pusher_t)
    return (pusher)

  def make_slot_plate(self):
    slots = CQ().add(self.slot_plate).toPending().extrude(self.slots_t)
    return (slots)

  def build(self):
    s = self
    asy = cadquery.Assembly()

    spacer = s.make_spacer_pcb()
    asy.add(spacer, name="spacer", color=cadquery.Color("DARKGREEN"))

    heater = s.make_heater_plate()
    asy.add(heater, name="heater", color=cadquery.Color("MATRAGRAY"))

    # the towerplate
    tp = self.make_tower_plate()
    asy.add(tp, name="towers", color=cadquery.Color("GOLDENROD"))

    asy.add(self.pcb, name="PCB", color=cadquery.Color("brown"))

    slots = self.make_slot_plate()
    asy.add(slots, name="Alignment Slots", color=cadquery.Color("GRAY"))

    pusher = self.make_pusher_plate()
    asy.add(pusher, name="Pusher Downer", color=cadquery.Color("GRAY"))



    # make the middle piece
    #middle, top_mid= self.make_middle(werkplane)
    #asy.add(middle, name="middle", color=cadquery.Color("orange"))
    #asy.add(top_mid, name="top_mid", color=cadquery.Color("yellow"))

    # make the top piece
    #top = self.make_top(x, y)
    #asy.add(vg, name="vg")

    # constrain assembly
    #asy.constrain('spacer@faces@<Z','heater@faces@>Z','Point')
    #asy.constrain("heater?top", "spacer?bot", "Axis")

    # solve constraints
    #asy.solve()

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
        cadquery.exporters.export(c, f'{val.name}.stl')

main()