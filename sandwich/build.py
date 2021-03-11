#!/usr/bin/env python3
import cadquery as cq
import geometrics.toolbox as tb
from geometrics.sandwich import Sandwich
import pathlib

def main():
    s = Sandwich(leng=166, wid=50, substrate_xy=30, cutout_spacing=35, endblock_width=12, aux_hole_spacing=16, block_offset_from_edge_of_base=1)
    
    cmpd = s.build()
    salads = cmpd.Solids()
    
    for salad in salads:
        if "show_object" in globals():
            show_object(salad)
        elif __name__ == "__main__":
            this_hash = salad.hashCode()  # this might not be unique because it does not hash orientation
            tb.utilities.export_step(salad, pathlib.Path(f"{this_hash}.step"))

main()
