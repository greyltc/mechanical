use <pcb_passthroughs.scad>;

plate_thickness = 12.14;

plate_dims=[168, 50, 12.14];

slot1loc = [154.83, 40, plate_thickness];
slot2loc = [154.83, 10, plate_thickness];
slot3loc = [13.17, 40, plate_thickness];
slot4loc = [13.17, 10, plate_thickness];

difference(){
    cube(plate_dims);
    translate(slot1loc) card_edge_passthrough(t=plate_thickness);
    translate(slot2loc) card_edge_passthrough(t=plate_thickness);
    translate(slot3loc) card_edge_passthrough(t=plate_thickness);
    translate(slot4loc) card_edge_passthrough(t=plate_thickness);
}
