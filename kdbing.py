##-----------------------------------------------------------------------------------
## eOn is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## A copy of the GNU General Public License is available at
## http://www.gnu.org/licenses/
##-----------------------------------------------------------------------------------

import subprocess
import os
import shutil
import signal
import glob
import numpy
import logging
logger = logging.getLogger('kdb')    

import config
import io



class KDB:


    def __init__(self):
        pass

    def add_process(self, state, process_id):
        logger.debug("Adding process.")
        try:
            os.makedirs(config.kdb_scratch_path)
        except OSError:
            pass
        mode = state.get_process_mode(process_id)
        f = open(os.path.join(config.kdb_scratch_path, "MODE"), 'w')
        for m in mode:
            f.write("%f %f %f\n" % (m[0], m[1], m[2]))
        f.close()
        sp = subprocess.Popen([config.kdb_addpath, 
                              state.proc_reactant_path(process_id), 
                              state.proc_saddle_path(process_id),
                              state.proc_product_path(process_id),
                              os.path.join(config.kdb_scratch_path, "MODE"),
                              "--kdbdir=%s" % config.kdb_path], 
                              stdout = subprocess.PIPE, 
                              stderr = subprocess.PIPE)
        sp.wait()
        return sp.communicate()[0].strip()
                

    def query(self, state, wait = False):
        # If the path already exists, remove it and create a new one.
        if os.path.isdir(config.kdb_scratch_path):
            # See if there is a PID file for a possibly already running query process.
            if os.path.exists(os.path.join(config.kdb_scratch_path, "PID")):
                # If so, try to kill it.
                f = open(os.path.join(config.kdb_scratch_path, "PID") , 'r')
                pid = int(f.readline())
                f.close()
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    # Probably wasn't running.
                    pass
            # Delete the scratch path.
            shutil.rmtree(config.kdb_scratch_path)        
        # Create the scratch path
        os.makedirs(config.kdb_scratch_path)
        kdbpath = os.path.abspath(os.path.join(config.path_root, config.kdb_path))
        rp = os.path.abspath(state.reactant_path)
        if state.number == 0:
            rp = os.path.abspath(os.path.join(config.path_root, "reactant.con"))
        sp = subprocess.Popen([config.kdb_querypath, rp, "--kdbdir=%s" % kdbpath], 
                              cwd = config.kdb_scratch_path,
                              stdout = subprocess.PIPE, 
                              stderr = subprocess.PIPE)
        # Save the PID of this running process.
        f = open(os.path.join(config.kdb_scratch_path, "PID"), 'w')
        f.write("%d" % sp.pid)
        f.close()
        if wait:
            sp.wait()


    def make_suggestion(self, keep_path = None):
        if os.path.isdir(os.path.join(config.kdb_scratch_path, "kdbmatches")):
            dones = glob.glob(os.path.join(config.kdb_scratch_path, "kdbmatches",".done_*"))
            if len(dones) > 0:
                number = dones[0].split("_")[1]
                displacement = io.loadcon(os.path.join(config.kdb_scratch_path, "kdbmatches", "SADDLE_%s" % number))
                mode = [[float(i) for i in l.strip().split()] for l in open(os.path.join(config.kdb_scratch_path, "kdbmatches", "MODE_%s" % number), 'r').readlines()[:]]
                if keep_path is not None:
                    if not os.path.isdir(keep_path):
                        os.mkdir(keep_path)
                    shutil.move(os.path.join(config.kdb_scratch_path, "kdbmatches", ".done_%s" % number), os.path.join(keep_path, ".done_%s" % number))
                    shutil.move(os.path.join(config.kdb_scratch_path, "kdbmatches", "SADDLE_%s" % number), os.path.join(keep_path, "SADDLE_%s" % number))
                    shutil.move(os.path.join(config.kdb_scratch_path, "kdbmatches", "MODE_%s" % number), os.path.join(keep_path, "MODE_%s" % number))
                else:
                    os.remove(os.path.join(config.kdb_scratch_path, "kdbmatches", ".done_%s" % number))
                    os.remove(os.path.join(config.kdb_scratch_path, "kdbmatches", "SADDLE_%s" % number))
                    os.remove(os.path.join(config.kdb_scratch_path, "kdbmatches", "MODE_%s" % number))
                return displacement, mode
        return None, None
                
            
    















