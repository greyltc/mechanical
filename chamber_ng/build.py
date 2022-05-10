from cadquery import cq, CQ
depth = 4
cutter_path = cq.Workplane("XY").rect(150, 150, centered=True).extrude(1).edges("|Z").fillet(10).faces("-Z").wires().val()

cp_tangent = cutter_path.tangentAt()  # tangent to cutter_path
cp_start = cutter_path.startPoint()
build_plane = cq.Plane(origin=cp_start, normal=cp_tangent)
half_profile = CQ(build_plane).polyline([(0, 0), (depth, 0), (0, -depth)]).close()
cutter = half_profile.revolve(axisEnd=(1,0,0))
cutter_split = cutter.split(keepTop=True)
cutter_crosssection = cutter_split.faces('|X').wires().val()

to_sweep = CQ(cutter_crosssection).wires().toPending()
sweep_result = to_sweep.sweep(cutter_path, combine=True, transition="round", sweepAlongWires=True, isFrenet=True)

show_object(cutter_path)
show_object(sweep_result)