#include"NewPotential.h"

NewPotential::NewPotential(void){
}

void NewPotential::initialize(void){
    fake1 = 0;
    fake2 = 1;
    return;
}

void NewPotential::cleanMemory(void){
    return;
}

// pointer to number of atoms, pointer to array of positions	
// pointer to array of forces, pointer to internal energy
// adress to supercell size
void NewPotential::force(long N, const double *R, const long *atomicNrs, double *F, double *U, const double *box){

    for(int i=0; i<N; i++){
        F[ 3*i ] = fake1;
        F[3*i+1] = fake1;
        F[3*i+2] = fake1;
    }
    
    *U = fake2;
    return;
}