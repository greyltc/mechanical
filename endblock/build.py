#!/usr/bin/env python3
import cadquery as cq
import geometrics.toolbox as tb
import pathlib

def main():
    block = tb.endblock.build(horzm3s=True, align_bumps=True, special_chamfer=1.6)
    
    if "show_object" in globals():
        show_object(block)
    elif __name__ == "__main__":
        tb.utilities.export_step(block, pathlib.Path(f"endblock.step"))

main()
