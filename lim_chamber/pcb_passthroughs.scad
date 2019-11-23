
$fn = 20;

// produces a shape to be subtracted from a plate for the PCB card-edge passthrough
// t = plate thickness
// location = [x,y,z] top-center of 
// con_clearance = clearance between mated connector and pocket on all sides
// con_len = length of connector (samtec MECF-08-01-L-DV-NP-WT=18.34, 20pos = 33.58)
// r = tool radius
// gp_buffer = glue pocket buffer space around PCB
// pcb_t = PCB tab thicness
// pcb_len = PCB tab length
// pcb_clearance = clearance around PCB in its slot
module card_edge_passthrough(location, con_len=18.34, con_clearance=0.05, t=12.14, r=1, gp_buffer=2, pcb_t=1.6, pcb_len=11.91, pcb_clearance=0.1){
    connector_height=8.5; //mm SAMTEC MECF-XX-01-L-DV-NP-WT
    connector_width=5.60; //mm SAMTEC MECF-XX-01-L-DV-NP-WT
    above_connector = t-connector_height;
    glue_pocket_depth = above_connector/2;
    gp_width = 2*gp_buffer + pcb_t;
    gp_len = 2*gp_buffer + pcb_len;
    
    difference(){
    square([gp_len,gp_width],center=true);
    translate([gp_len/2-r,gp_width/2-r,0]) translate([0,0,0]) difference(){
        square([r,r]);
        circle(r=r);
        }
    difference(){
        translate([-r,-r,0]) square([r,r]);
        circle(r=r);
        }
    difference(){
        translate([-r,0,0]) square([r,r]);
        circle(r=r);
        }
    difference(){
        translate([0,-r,0]) square([r,r]);
        circle(r=r);
        }
    }

    
    // connector pocket corner coordinates
    con_cornerA = [con_len/2+con_clearance, connector_width/2+con_clearance];
    con_cornerB = [-con_len/2-con_clearance, -connector_width/2-con_clearance];
    con_cornerC = [-con_len/2-con_clearance, connector_width/2+con_clearance];
    con_cornerD = [con_len/2+con_clearance, -connector_width/2-con_clearance];
    translate([location[0],location[1],location[2]+(connector_height+con_clearance)/2-t]) {
        // socket well with drilled corners
        union(){
            cube([con_len+2*con_clearance,connector_width+2*con_clearance,connector_height+con_clearance],center=true);
            translate([con_cornerA[0]-r/sqrt(2),con_cornerA[1]-r/sqrt(2)]) cylinder(r=r,h=connector_height+con_clearance,center=true);
            translate([con_cornerB[0]+r/sqrt(2),con_cornerB[1]+r/sqrt(2)]) cylinder(r=r,h=connector_height+con_clearance,center=true);
            translate([con_cornerC[0]+r/sqrt(2),con_cornerC[1]-r/sqrt(2)]) cylinder(r=r,h=connector_height+con_clearance,center=true);
            translate([con_cornerD[0]-r/sqrt(2),con_cornerD[1]+r/sqrt(2)]) cylinder(r=r,h=connector_height+con_clearance,center=true);
        } // end union
    } // end translate
} // end module


card_edge_passthrough([0,0,0]);