/*
 *===============================================
 *  EON Parameters.cpp
 *===============================================
 */

#include <errno.h>
#include "Parameters.h"
#include "INIFile.h"

Parameters::Parameters(){

    // Default values

    jobType = PROCESS_SEARCH;
    randomSeed = -1;
    reactantStateTag = 0;
    potentialTag = 1;
    potentialNoTranslation = 0;
    getPrefactorsTag = 0;
    minimizeOnly = 0;
    minimizeBox = 0;
    maxDifferencePos = 0.1;

    /*
    This is now defined in Epicenters, but it should be moved back as a parameter
    neighborCutoff = 3.3; 
    */
    
    // default parameter for relaxation   
    convergedRelax = 0.005;

    // default parameters for process search
    processSearchMinimizeFirst = 0;

    // default parameters for saddle point determination   
    saddleTypePerturbation = 1;
    saddleRefine = false;
    saddleLowestEigenmodeDetermination = 1;
    saddleConverged = 0.025;
    saddleMaxJumpAttempts = 0;
    saddleMaxStepSize = 0.2;
    saddleMaxEnergy = 20.0;
    saddleNormPerturbation = 0.1;
    saddleWithinRadiusPerturbated = 4.0;
    saddleMaxSinglePerturbation = 0.1;
    saddleMaxIterations = 512;
    saddleMaxIterationsConcave = 256;
    saddlePerpendicularForceRatio = 0.0;

    // default parameters for Hessian determination   
    hessianMaxSize = 0;
    hessianMinDisplacement = 0.25;
    hessianWithinRadiusDisplaced = 5.0;
    hessianPrefactorMax = 10e20;
    hessianPrefactorMin = 10e8;

    // default parameters the dimer method
    dimerRotations = 1;
    dimerSeparation = 0.0001;
    dimerRotationAngle = 0.005;
    
    // default parameters used by the optimizers
    maximumIterations=512;
    cgCurvatureStep = 0.001;
    cgMaxMoveFullRelax = 0.2;
    qmTimeStep = 0.1;

    //default parameters used by Parallel Repica Dynamics
    mdTimeStep = 0.1;
    mdTemperture = 300.0;
    mdSteps = 1000;
    PRD_MaxMovedDist = 2.0;
    mdRefine = false;
    RefineAccuracy = 20;
    CheckFreq = 500;
    NewRelaxSteps = 500;
   
    //default parameters used by Thermostat
    Andersen_Alpha=0.2; //collision strength
    Andersen_Tcol=10; //collision frequency in unit of dt
    return;
}

Parameters::~Parameters(){
    return;
}

string Parameters::toLowerCase(string s)
{
    for (string::size_type i = 0; i < s.length(); ++i) {
      s[i] = tolower(s[i]);
    }
    return s;
}

int Parameters::load(string filename)
{
    FILE *fh;

    fh = fopen(filename.c_str(), "rb");
    if (fh == NULL) {
        fprintf(stderr, "problem loading parameters file:%s\n", strerror(errno));
        return 1;
    }
    int error = load(fh);
    fclose(fh);
    return error;
}

int Parameters::load(FILE *file){
    
    CIniFile ini;
    ini.CaseInsensitive();
    int error=0;
    if(ini.ReadFile(file))
    {
        // if we succesfully read the file, then parse it as an INI
        randomSeed = ini.GetValueL("Default", "RANDOM_SEED", randomSeed);
        potentialTag = ini.GetValueL("Default", "POTENTIAL_TAG", potentialTag);
        potentialNoTranslation = ini.GetValueL("Default", 
                                               "POTENTIAL_NO_TRANSLATION", 
                                               potentialNoTranslation);
        minimizeOnly = ini.GetValueL("Default", "MINIMIZE_ONLY", minimizeOnly);
        minimizeBox = ini.GetValueL("Default", "MINIMIZE_BOX", minimizeBox);
        convergedRelax = ini.GetValueF("Default", "CONVERGED_RELAX", 
                                       convergedRelax);
        maximumIterations = ini.GetValueL("Default", "MAXIMUM_ITERATIONS",
                                          maximumIterations);

        string jobTypeString;
        jobTypeString = ini.GetValue("Default", "JOB_TYPE", "processsearch");
        jobTypeString = toLowerCase(jobTypeString);

        if (jobTypeString == "processsearch") {
            jobType = PROCESS_SEARCH;
        }else if (jobTypeString == "saddlesearch") {
            jobType = SADDLE_SEARCH;
        }else if (jobTypeString == "minimization") {
            jobType = MINIMIZATION;
		}else if (jobTypeString == "parallelreplica"){
				jobType = PARALLEL_REPLICA;
        }else{
            fprintf(stderr, "Unknown JOB_TYPE: %s\n", jobTypeString.c_str());
            error = 1;
        }

        processSearchMinimizeFirst = ini.GetValueL("ProcessSearch", "minimize_first",
                                                   processSearchMinimizeFirst);
        
        saddleTypePerturbation = ini.GetValueL("Saddle_Point", "TYPE_PERTURBATION",
                                               saddleTypePerturbation);
        saddleLowestEigenmodeDetermination = 
            ini.GetValueL("Saddle_Point", "LOWEST_EIGENMODE_DETERMINATION", 
                          saddleLowestEigenmodeDetermination);
        saddleRefine = ini.GetValueB("Saddle_Point", "REFINE", saddleRefine);
        saddleConverged = ini.GetValueF("Saddle_Point", "CONVERGED",
                                        saddleConverged);
        saddleMaxJumpAttempts = ini.GetValueL("Saddle_Point", "MAX_JUMP_ATTEMPTS",
                                              saddleMaxJumpAttempts);
        saddleMaxStepSize = ini.GetValueF("Saddle_Point", "MAX_STEP_SIZE",
                                          saddleMaxStepSize);
        saddleMaxEnergy = ini.GetValueF("Saddle_Point", "MAX_ENERGY", 
                                        saddleMaxEnergy);
        saddleNormPerturbation = ini.GetValueF("Saddle_Point", "NORM_PERTURBATION",
                                               saddleNormPerturbation);
        saddleMaxSinglePerturbation = ini.GetValueF("Saddle_Point",
                                                    "MAX_SINGLE_PERTURBATION",
                                                    saddleMaxSinglePerturbation);
        saddleWithinRadiusPerturbated = ini.GetValueF("Saddle_Point",
                                                      "WITHIN_RADIUS_PERTURBATED",
                                                      saddleWithinRadiusPerturbated);
        saddleMaxIterations = ini.GetValueL("Saddle_Point", 
                                            "MAX_ITERATIONS", 
                                            saddleMaxIterations);
        saddlePerpendicularForceRatio = ini.GetValueF("Default",
                                                      "PERPENDICULAR_FORCE_RATIO",
                                                      saddlePerpendicularForceRatio);

        hessianMaxSize = ini.GetValueL("Hessian", "MAX_SIZE", hessianMaxSize);
        hessianWithinRadiusDisplaced = ini.GetValueF("Hessian", 
                                                     "WITHIN_RADIUS_DISPLACED",
                                                     hessianWithinRadiusDisplaced);
        hessianMinDisplacement = ini.GetValueF("Hessian", 
                                               "MIN_DISPLACEMENT",
                                               hessianMinDisplacement);
        
        dimerRotations = ini.GetValueL("Dimer", "ROTATIONS", dimerRotations);
        dimerSeparation = ini.GetValueF("Dimer", "SEPARATION", dimerSeparation);
        dimerRotationAngle = ini.GetValueF("Dimer", "ANGLE", dimerRotationAngle);

	mdTimeStep = ini.GetValueF("Dynamics","TIMESTEP",mdTimeStep);
	mdTemperture = ini.GetValueF("Dynamics","TEMPERTURE",mdTemperture);
	mdSteps = ini.GetValueL("Dynamics","STEPS",mdSteps);
	PRD_MaxMovedDist = ini.GetValueF("Dynamics","PRD_MaxMovedDist",PRD_MaxMovedDist);  
	mdRefine = ini.GetValueB("Dynamics","mdRefine",mdRefine);
	RefineAccuracy = ini.GetValueL("Dynamics","STEPS",RefineAccuracy);
	CheckFreq = ini.GetValueL("Dynamics","CheckFreq",CheckFreq);
        NewRelaxSteps = ini.GetValueL("Dynamics","NewRelaxStep",NewRelaxSteps);

        cgCurvatureStep = ini.GetValueF("CG","CURVATURE_STEP", cgCurvatureStep);


	Andersen_Alpha = ini.GetValueF("Thermo","ANDERSEN_ALPHA",Andersen_Alpha);
	Andersen_Tcol = ini.GetValueF("Thermo","ANDERSEN_TCOL",Andersen_Tcol);

    }
    else
    {
        fprintf(stderr, "Couldn't parse the ini file. Perhaps you are "
                        "using the old style config?\n");
        error = 1;
    }
    return error;
}