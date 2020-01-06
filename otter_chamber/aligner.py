wp = cq.Workplane("XY")

bw = 23.8
bh = 15
bd = 5.5

mount_space = 16

below_zero = 15

al = wp.rect(bw,15,centered=True).extrude(5.5)
al = al.faces("<Z").rect(bw,15,centered=True).extrude(-below_zero)
#block = block.box(bw,15,-10,centered=(True,True,False))


al=al.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(-2.5,-3.3).hole(4,6.5)
al=al.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(-12.5,-1.6750).hole(5,3)


# make the top step
not_up = 7.8
steph = bh-not_up
al=al.faces(">Z").workplane(centerOption='CenterOfBoundBox').center(-bw/2,bh/2-not_up).rect(bw,not_up,centered=False).cutBlind(-3)

# make the bottom step

al=al.faces("<Z").workplane(centerOption='CenterOfBoundBox').center(-bw/2,4).rect(bw,-30,centered=False).cutBlind(-below_zero)

# TODO: chamfer the holes on all sides


# make the mounts
side_face = al.faces("<Y").workplane(centerOption='CenterOfBoundBox')
side_face = side_face.pushPoints([(mount_space/2, -0.25), (-mount_space/2,-0.25)])
al = side_face.cskHole(3.2, cskDiameter=5, cskAngle=90, clean=True)

al = al.faces("<X").edges().chamfer(0.5)
al = al.faces(">X").edges().chamfer(0.5)
al = al.faces("<Z").edges("|X").chamfer(0.5)
al = al.faces(">Y").edges("|X").chamfer(0.5)
al = al.faces(">Z").edges("|X").chamfer(0.5)
