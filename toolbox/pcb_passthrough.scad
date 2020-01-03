
$fn = 60;


// kinda like the built-in square() function except it will produce rounded corners with radius r
// drill=true means the corners will be drilled out
module square_rounded(size, r=1, drill=false, center=true){
    offsetx =   center ? 0 : size[0]/2 ;
    offsety =   center ? 0 : size[1]/2 ;
    translate([offsetx, offsety, 0]){
        if (drill == false){
            difference(){// subtract away the corners to get rounds
                square(size, center=true);
                translate([size[0]/2-r,size[1]/2-r,0]) difference(){
                    translate([0,0,0]) square([r,r]);
                    circle(r=r);
                }
                translate([-size[0]/2+r,-size[1]/2+r,0]) difference(){
                    translate([-r,-r,0]) square([r,r]);
                    circle(r=r);
                }
                translate([-size[0]/2+r,size[1]/2-r,0]) difference(){
                    translate([-r,0,0]) square([r,r]);
                    circle(r=r);
                }
                translate([size[0]/2-r,-size[1]/2+r,0]) difference(){
                    translate([0,-r,0]) square([r,r]);
                    circle(r=r);
                }
            }
        } else { // drill is true
            union(){
                square(size, center=true);
                translate([size[0]/2-r/sqrt(2), size[1]/2-r/sqrt(2)]) circle(r=r);
                translate([-size[0]/2+r/sqrt(2), -size[1]/2+r/sqrt(2)]) circle(r=r);
                translate([-size[0]/2+r/sqrt(2), size[1]/2-r/sqrt(2)]) circle(r=r);
                translate([size[0]/2-r/sqrt(2), -size[1]/2+r/sqrt(2)]) circle(r=r);
            }
        } // end drill or not
    } // end translate
} // end module

// produces a shape to be subtracted from a plate for the PCB card-edge passthrough at [0,0,0]
// t = plate thickness

// rows = number of rows of the samtec MECF-DV connector we'll make a pocket for (must be 8 or 20)
// con_clearance = clearance between mated connector and pocket on all sides
// r = tool radius
// r_pcb = PCB slot tool radius
// gp_buffer = glue pocket buffer space around PCB
// pcb_t = PCB tab thickness
// pcb_clearance = clearance around PCB in its slot
// length for allignment fillets
module card_edge_passthrough(rows=8, con_clearance=0.10, t=12, r=1.5, gp_buffer=2, pcb_t=1.6, r_pcb=0.5, pcb_clearance=0.1, fillet_length=1.5){
    connector_height=8.78+0.15; //mm SAMTEC MECF-XX-01-L-DV-NP-WT (worst case (largest) size)
    connector_width=5.6+0.13; //mm SAMTEC MECF-XX-01-L-DV-NP-WT (worst case (largest) size)

    con_len = (rows==8)?18.34+0.13:(rows==20)?33.58+0.13:NaN;
    pcb_len = (rows==8)?11.91:(rows==20)?27.15:NaN;

    // calculate connector pocket corner coordinates
    cp_len = con_len+2*con_clearance; // length of connector pocket
    cp_width = connector_width+2*con_clearance; // width of connector pocket
    con_cornerA = [cp_len/2, cp_width/2];
    con_cornerB = [-cp_len/2, -cp_width/2];
    con_cornerC = [-cp_len/2, cp_width/2];
    con_cornerD = [cp_len/2, -cp_width/2];
    
    // calculations for fillet polyhedron thing
    fillet_corner0 = [con_cornerB[0] - fillet_length, con_cornerB[1] - fillet_length, -t];
    fillet_corner1 = [con_cornerC[0] - fillet_length, con_cornerC[1] + fillet_length, -t];
    fillet_corner2 = [con_cornerA[0] + fillet_length, con_cornerA[1] + fillet_length, -t];
    fillet_corner3 = [con_cornerD[0] + fillet_length, con_cornerD[1] - fillet_length, -t];
    fillet_corner4 = [con_cornerB[0], con_cornerB[1], -t + fillet_length];
    fillet_corner5 = [con_cornerC[0], con_cornerC[1], -t + fillet_length];
    fillet_corner6 = [con_cornerA[0], con_cornerA[1], -t + fillet_length];
    fillet_corner7 = [con_cornerD[0], con_cornerD[1], -t + fillet_length];
    p_points =[ fillet_corner0, fillet_corner1, fillet_corner2, fillet_corner3, fillet_corner4, fillet_corner5, fillet_corner6, fillet_corner7 ];
    p_faces = [ [0,1,2,3], [4,5,1,0], [7,6,5,4], [5,6,2,1], [6,7,3,2], [7,4,0,3] ];
    
    // calculate some glue pocket parameters
    above_connector = t-connector_height-con_clearance; // space above the connector pocket
    echo(above_connector);
    gp_width = 2*gp_buffer + pcb_t; // width of glue pocket
    gp_len = 2*gp_buffer + pcb_len; // length of glue pocket
    glue_pocket_depth = above_connector/2; // depth of glue pocket
    
    union(){
        // fabricate the board slot
        translate([0,0,-t]) linear_extrude(t) square_rounded([pcb_len+2*pcb_clearance, pcb_t+2*pcb_clearance], r=r_pcb, drill=true);
        
        // fabricate the rounded corner glue pocket
        translate([0,0,-glue_pocket_depth]) linear_extrude(glue_pocket_depth) square_rounded([gp_len, gp_width], r=r);
        
        // fabricate connector socket well with drilled corners
        translate([0,0,-t]) linear_extrude(connector_height+con_clearance) square_rounded([cp_len, cp_width], r=r, drill=true);
        
        // fabriate fillet guide base
        polyhedron( points=p_points, faces=p_faces);
    } // end union top level union
} // end module


card_edge_passthrough();