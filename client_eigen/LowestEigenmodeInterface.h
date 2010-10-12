/*
 *===============================================
 *  EON LowestEigenmodeInterface.h
 *===============================================
 */

#ifndef LOWEST_EIGENMODE_INTERFACE_H
#define LOWEST_EIGENMODE_INTERFACE_H

#include "Matter.h"

#include "Parameters.h"

/* Define the interface for the lowest eigenvalue determination algorithm */
class LowestEigenmodeInterface{
public:
    virtual ~LowestEigenmodeInterface(){};
    void virtual startNewSearchAndCompute(Matter const *matter, double *displacement) = 0; 
    void virtual moveAndCompute(Matter const *matter) = 0;  
    double virtual returnLowestEigenmode(double *result) = 0;
    /// Return eigenvector.
    virtual double const * getEigenvector(long & size) const
    {size=0; return 0;}
        /** Set initial direction manually.*/
    virtual void setEigenvector(long size, double const eigenvector[]) {}
};
#endif