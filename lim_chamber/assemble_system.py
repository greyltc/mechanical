#!/usr/bin/env python

import cadquery as cq

pcb_project = "lim_crossbar"
crossbar_step_file_name = f"../../electronics/{pcb_project}/3dOut/{pcb_project}.step"
crossbar = cq.importers.importStep(crossbar_step_file_name)
crossbar = crossbar.translate((0,0,-1.6/2))
crossbar = crossbar.rotate((0,0,0),(1,0,0), 90)
crossbar = crossbar.translate((0,0,23.67))
crossbar = crossbar.translate((168/2,0,0))
assembly = crossbar.translate((0,10,0))
assembly.add(crossbar.translate((0,40,0)))

passthrough_step_file = "pcb_passthroughs.step"
passthrough = cq.importers.importStep(passthrough_step_file)
assembly.add(passthrough)


pcb_project = "ox_30_by_30"
adapter_step_file_name = f"../../electronics/{pcb_project}/3dOut/{pcb_project}.step"
adapter = cq.importers.importStep(adapter_step_file_name)
adapter = adapter.rotate((0,0,0),(0,0,1), 90)
adapter = adapter.translate((41.5,25,29.64+1.5))
assembly.add(adapter)
assembly.add(adapter.translate((42.5,0,0)))
assembly.add(adapter.translate((85,0,0)))

assembly = assembly.rotate((0,0,0),(1,0,0), -90)
assembly = assembly.translate((16, 16.5+1.6,75))
show_object(assembly)

chamber_step_file = "chamber.stp"
chamber_corner_offset = (107.267, 133.891, 137.882)
chamber = cq.importers.importStep(chamber_step_file)
chamber = chamber.translate(chamber_corner_offset)
show_object(chamber)

