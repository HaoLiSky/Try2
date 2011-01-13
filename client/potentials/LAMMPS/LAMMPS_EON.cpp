#include "LAMMPS_EON.h"

// General Functions
lammps_eon::lammps_eon(void){
    numberOfAtoms = 0;
}

void lammps_eon::cleanMemory(void){
    if(LAMMPSObj != NULL){
        lammps_close(LAMMPSObj);
        LAMMPSObj = NULL;
    }
    return;
}

// pointer to number of atoms, pointer to array of positions	
// pointer to array of forces, pointer to internal energy
// adress to supercell size
void lammps_eon::force(long N, const double *R, const int *atomicNrs,
                       double *F, double *U, const double *box){
    double *pos = new double[3*N];
    int i;

    if (numberOfAtoms != N){
        makeNewLAMMPS(N, box);
    }    
    for(i=0; i<3*N; i++){
        pos[i] = R[i];
    }
    lammps_put_coords(LAMMPSObj, pos);
    lammps_command(LAMMPSObj,"run 0");  
    *U = lammps_get_energy(LAMMPSObj);
    lammps_get_forces(LAMMPSObj,F);

    delete [] pos;
    return;
}

void lammps_eon::makeNewLAMMPS(long N, const double *box){
    if(LAMMPSObj != NULL){
        cleanMemory();
    }
    
    // creates configuration file that is read in when LAMMPS initialize
    FILE *fp;
    fp = fopen("lammps.conf","w");
    fprintf(fp, "Created by EON\n");
    fprintf(fp, "\n%d atoms\n", N);
    fprintf(fp, "1 atom types\n");
    fprintf(fp, "0.0   %f  xlo xhi\n", box[0]);
    fprintf(fp, "0.0   %f  ylo yhi\n", box[4]);
    fprintf(fp, "0.0   %f  zlo zhi\n", box[8]);
    fprintf(fp, "\nMasses\n");
    fprintf(fp, "\n1 1\n");
    fprintf(fp, "\nAtoms\n\n");
    for(int i=0; i<N; i++){
        fprintf(fp, "  %i 1  0. 0. 0.\n", i+1);
    }
    fclose(fp);

 //printf("opening lammps\n");
    // opens and read LAMMPS input script
    lammps_open_no_mpi(0, NULL, (void**) &LAMMPSObj);
    int n;
    char line[1024];
    fp = fopen("lammps.in","r");
    if (fp == NULL) {
        printf("ERROR: Could not open lammps.in (LAMMPS input script)\n");
    }
    while (1) {
        if (fgets(line,1024,fp) == NULL){
            n = 0;
        }
        else{ 
            n = strlen(line) + 1;
        }
        if (n == 0){ 
            fclose(fp);
            break;
        }
        LAMMPSObj->input->one(line);
    }  
//printf("lammps initialized\n");
    return;
}

