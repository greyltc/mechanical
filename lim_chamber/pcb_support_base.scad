use <pcb_passthroughs.scad>;

plate_thickness = 12.14;

plate_dims=[168, 50];
window_dims=[120,30];

slot1loc = [154.83, 40, plate_thickness];
slot2loc = [154.83, 10, plate_thickness];
slot3loc = [13.17, 40, plate_thickness];
slot4loc = [13.17, 10, plate_thickness];

difference(){
    linear_extrude(plate_thickness) square_rounded(plate_dims, center=false, r=3);
    translate(slot1loc) card_edge_passthrough(t=plate_thickness);
    translate(slot2loc) card_edge_passthrough(t=plate_thickness);
    translate(slot3loc) card_edge_passthrough(t=plate_thickness);
    translate(slot4loc) card_edge_passthrough(t=plate_thickness);
    translate([plate_dims[0]/2, plate_dims[1]/2, 0]) linear_extrude(plate_thickness) square_rounded(window_dims, center=true, r=3, drill=true);
}
