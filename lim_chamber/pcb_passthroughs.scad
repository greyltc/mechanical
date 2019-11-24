
//$fn = 20;

// produces a shape to be subtracted from a plate for the PCB card-edge passthrough
// t = plate thickness
// location = [x,y,z] top-center of 
// con_clearance = clearance between mated connector and pocket on all sides
// con_len = length of connector (samtec MECF-08-01-L-DV-NP-WT=18.34, 20pos = 33.58)
// r = tool radius
// gp_buffer = glue pocket buffer space around PCB
// pcb_t = PCB tab thickness
// pcb_len = PCB tab length
// pcb_clearance = clearance around PCB in its slot
// length for allignment fillets
module card_edge_passthrough(location, con_len=18.34, con_clearance=0.05, t=12.14, r=1, gp_buffer=2, pcb_t=1.6, pcb_len=11.91, pcb_clearance=0.1, fillet_length=1.5){
    connector_height=8.5; //mm SAMTEC MECF-XX-01-L-DV-NP-WT
    connector_width=5.60; //mm SAMTEC MECF-XX-01-L-DV-NP-WT
    
    // calculate connector pocket corner coordinates
    con_cornerA = [con_len/2+con_clearance, connector_width/2+con_clearance];
    con_cornerB = [-con_len/2-con_clearance, -connector_width/2-con_clearance];
    con_cornerC = [-con_len/2-con_clearance, connector_width/2+con_clearance];
    con_cornerD = [con_len/2+con_clearance, -connector_width/2-con_clearance];
    
    // calculate connector pocket fillet polyhedron coordinates

    fillet_corner0 = [con_cornerB[0] - fillet_length, con_cornerB[1] - fillet_length, -t];
    fillet_corner1 = [con_cornerC[0] - fillet_length, con_cornerC[1] + fillet_length, -t];
    fillet_corner2 = [con_cornerA[0] + fillet_length, con_cornerA[1] + fillet_length, -t];
    fillet_corner3 = [con_cornerD[0] + fillet_length, con_cornerD[1] - fillet_length, -t];
    fillet_corner4 = [con_cornerB[0], con_cornerB[1], -t + fillet_length];
    fillet_corner5 = [con_cornerC[0], con_cornerC[1], -t + fillet_length];
    fillet_corner6 = [con_cornerA[0], con_cornerA[1], -t + fillet_length];
    fillet_corner7 = [con_cornerD[0], con_cornerD[1], -t + fillet_length];
    
    // calculate some glue pocket parameters
    above_connector = t-connector_height; // space above the connector pocket
    gp_width = 2*gp_buffer + pcb_t; // width of glue pocket
    gp_len = 2*gp_buffer + pcb_len; // length of glue pocket
    glue_pocket_depth = above_connector/2; // depth of glue pocket
    
    union(){
        // fabricate the board slot
        translate([0,0,-t/2]) cube([pcb_len+2*pcb_clearance, pcb_t+2*pcb_clearance,t], center=true);
        
        // fabricate the rounded corner glue pocket
        translate([0,0,-glue_pocket_depth]) linear_extrude(glue_pocket_depth) difference(){// subtract away the corners to get rounds
        square([gp_len,gp_width],center=true);
        translate([gp_len/2-r,gp_width/2-r,0]) difference(){
            translate([0,0,0]) square([r,r]);
            circle(r=r);
            }
        translate([-gp_len/2+r,-gp_width/2+r,0]) difference(){
            translate([-r,-r,0]) square([r,r]);
            circle(r=r);
            }
        translate([-gp_len/2+r,gp_width/2-r,0]) difference(){
            translate([-r,0,0]) square([r,r]);
            circle(r=r);
            }
        translate([gp_len/2-r,-gp_width/2+r,0]) difference(){
            translate([0,-r,0]) square([r,r]);
            circle(r=r);
            }
        } // end difference
        
        // fabricate connector socket well with drilled corners
        translate([location[0],location[1],location[2]+(connector_height+con_clearance)/2-t]) union(){ // socket well with drilled corners
            cube([con_len+2*con_clearance,connector_width+2*con_clearance,connector_height+con_clearance],center=true);
            translate([con_cornerA[0]-r/sqrt(2),con_cornerA[1]-r/sqrt(2)]) cylinder(r=r,h=connector_height+con_clearance,center=true);
            translate([con_cornerB[0]+r/sqrt(2),con_cornerB[1]+r/sqrt(2)]) cylinder(r=r,h=connector_height+con_clearance,center=true);
            translate([con_cornerC[0]+r/sqrt(2),con_cornerC[1]-r/sqrt(2)]) cylinder(r=r,h=connector_height+con_clearance,center=true);
            translate([con_cornerD[0]-r/sqrt(2),con_cornerD[1]+r/sqrt(2)]) cylinder(r=r,h=connector_height+con_clearance,center=true);
        } // end socket well union
        
        // fabricate the fillet polyhedron
//        polyhedron(
//  points=[ fillet_corner0, fillet_corner1, fillet_corner2, fillet_corner3, // the four points at base
//           fillet_corner4  ],                                 // the apex point 
//  faces=[ [0,1,4],[1,2,4],[2,3,4],[3,0,4],              // each triangle side
//              [1,0,3],[2,1,3] ]                         // two triangles for square base
// );

//        p_faces = [ [0,1,4],[1,2,4],[2,3,4],[3,0,4],              // each triangle side
//              [1,0,3],[2,1,3] ];                         // two triangles for square base
//        polyhedron(
//  points=[ fillet_corner0, fillet_corner1, fillet_corner2, fillet_corner3, // the four points at base
//           fillet_corner4  ],                                 // the apex point 
//  faces=p_faces                       // two triangles for square base
        
        p_faces = [
  [0,1,2,3],  // bottom
  [4,5,1,0],  // front
  [7,6,5,4],  // top
  [5,6,2,1],  // right
  [6,7,3,2],  // back
  [7,4,0,3]]; // left
        polyhedron(
  points=[ fillet_corner0, fillet_corner1, fillet_corner2, fillet_corner3, // the four points at base
           fillet_corner4, fillet_corner5, fillet_corner6, fillet_corner7  ],                                 // the apex point 
  faces=p_faces                       // two triangles for square base
 );
    } // end union top level union
} // end module


card_edge_passthrough([0,0,0]);