#!/usr/bin/env python3

# import geometrics.toolbox as tb
from geometrics.toolbox.twod_to_threed import TwoDToThreeD
from pathlib import Path

print(Path.cwd())


def main():
    # define where we'll read shapes from
    sources = [
        Path.cwd() / "drawings" / "2d.dxf",
    ]

    # instructions for 2d->3d
    instructions = []
    copper_color = "COPPER"
    copper_thickness = 5

    instructions.append(
        {
            "name": "tco_150x150mm",
            "layers": [
                {
                    "name": "copper_base",
                    "color": copper_color,
                    "thickness": copper_thickness,
                    "drawing_layer_names": ["cu_base", "corner_holes"],
                },
            ],
        }
    )

    ttt = TwoDToThreeD(instructions=instructions, sources=sources)
    to_build = [""]
    asys = ttt.build(to_build)

    TwoDToThreeD.outputter(asys)


# temp is what we get when run via cq-editor
if __name__ in ["__main__", "temp"]:
    main()
