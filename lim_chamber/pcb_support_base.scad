use <../toolbox/pcb_passthrough.scad>;

plate_thickness = 12;

plate_dims=[168,50];
window_dims=[120,30];

// taken from PCB design
pcb_tab_spacing = 141.66;
adapter_dim = 30;

slot1loc = [plate_dims[0]/2+pcb_tab_spacing/2, plate_dims[1]/2+adapter_dim/2, plate_thickness];
slot2loc = [plate_dims[0]/2+pcb_tab_spacing/2, plate_dims[1]/2-adapter_dim/2, plate_thickness];
slot3loc = [plate_dims[0]/2-pcb_tab_spacing/2, plate_dims[1]/2+adapter_dim/2, plate_thickness];
slot4loc = [plate_dims[0]/2-pcb_tab_spacing/2, plate_dims[1]/2-adapter_dim/2, plate_thickness];

difference(){
    linear_extrude(plate_thickness) square_rounded(plate_dims, center=false, r=3);
    translate(slot1loc) card_edge_passthrough(t=plate_thickness);
    translate(slot2loc) card_edge_passthrough(t=plate_thickness);
    translate(slot3loc) card_edge_passthrough(t=plate_thickness);
    translate(slot4loc) card_edge_passthrough(t=plate_thickness);
    translate([plate_dims[0]/2, plate_dims[1]/2, 0]) linear_extrude(plate_thickness) square_rounded(window_dims, center=true, r=3, drill=true);
}
