//-----------------------------------------------------------------------------------
// eOn is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// A copy of the GNU General Public License is available at
// http://www.gnu.org/licenses/
//-----------------------------------------------------------------------------------

#include "StructureComparisonJob.h"
#include "Optimizer.h"
#include "Log.h"
#include "Matter.h"
#include "HelperFunctions.h"

StructureComparisonJob::StructureComparisonJob(Parameters *params)
{
    parameters = params;
}

StructureComparisonJob::~StructureComparisonJob(){ }

std::vector<std::string> StructureComparisonJob::run(void)
{
    std::vector<std::string> returnFiles;

    Matter matter1(parameters);
    matter1.con2matter("matter1.con");
    Matter matter2(parameters);
    matter2.con2matter("matter2.con");

    if (matter1 == matter2) {
        printf("structures match\n");
    }else{
        printf("structures do not match\n");
    }

    return returnFiles;
}