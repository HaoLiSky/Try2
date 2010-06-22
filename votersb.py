import random
import math
import time
import os

import numpy
import logging
logger = logging.getLogger('votersb')

ID, ENERGY, PREFACTOR, PRODUCT, PRODUCT_ENERGY, PRODUCT_PREFACTOR, BARRIER, RATE, REPEATS = range(9)
processtable_head_fmt = "%7s %16s %11s %9s %16s %17s %8s %12s %7s\n"
mod_processtable_head_fmt = "%7s %16s %11s %9s %16s %17s %8s %12s %12s\n"
processtable_header = processtable_head_fmt % ("proc #", "saddle energy", "prefactor", "product", "product energy", "product prefactor", "barrier", "rate", "repeats")
mod_processtable_header = processtable_head_fmt % ("proc #", "saddle energy", "prefactor", "product", "product energy", "product prefactor", "barrier", "rate", "view count")
processtable_line = "%7d %16.5f %11.5e %9d %16.5f %17.5e %8.5f %12.5e %7d\n"

# --- Defining the "acceleration" parameters ---
# Should these be set in the configuration file?

# delta is more or less a measure of maximum error encountered as a result of using this method.
# Smaller values of delta correspond to higher assurance that the superbasin exiting will be correct
# with respect to exit time and direction (and smaller computational speed-up).
delta = 0.1

# alpha is the factor by which the rate constants are lowered when the superbasin criterion is passed.
# In general Chatterjee & Voter found 2 to be an acceptable value,
# but if there are "overlapping timescales", it should be less than the square root of gamma.
alpha = 2

# gamma determines what is a "high" barrier in the superbasin criterion.
# If a barrier is *not* a "high" barrier, *and* it has a low process count, the criterion fails.
# Thus if all "low-barrier" processes connected to the "current state" by other "low-barrier" processes
# have a high enough process count, then all of these processes will have their barriers raised
gamma = 2

# Nf is the number of times to have seen a process before performing the superbasin criterion.
# This comes from eq. 10 from the Chatterjee & Voter paper
Nf = math.ceil((alpha-1)/delta*math.log(1/delta))

class VoterSB:
    """ This is a class to keep track of things associated with performing the Chatterjee & Voter Accelerated Superbasin KMC method. """


    def __init__(self, kT, states, path_root, thermal_window):
        self.kT = kT
        self.Beta = 1/(kT)
        self.path = path_root
        self.thermal_window = thermal_window
        self.states = states

    def compile_process_table(self, current_state):
        """ Load the normal process table, and replace all the rates edited by AS-KMC. """
        current_state_procs_compiled = self.get_real_process_table(current_state)
        current_state_mod_procs = self.get_modified_process_table(current_state)
        for process_id in current_state_mod_procs.keys():
            try:
                current_state_procs_compiled[process_id] = current_state_mod_procs[process_id]
            except KeyError:
                # An exception is raised:
                # If the process is somehow in the modified process list, but it's not
                # in the normal list, there's a problem.
                raise Exception("Somehow the modified process table has a process that\
                    the 'comprehensive' process list does not.  That's a problem...")
        return current_state_procs_compiled

    def get_ratetable(self, current_state):
        """ Generate a rate table according to the kT and thermal_window. """
        current_state_procs = self.compile_process_table(current_state)
        lowest = current_state.get_lowest_barrier()
        table = []
        for process_id in current_state_procs.keys():
            proc = current_state_procs[process_id]
            if proc["barrier"] < lowest + (self.kT * self.thermal_window):
                table.append((process_id, proc["rate"]))
        return table

    def get_askmc_metadata(self):
        """ Check to see if the AS-KMC data has been saved.
            If it hasn't, simply use the correct starting values.
            Otherwise, read the current values. """
            # "sb_check_count" is a method to reduce the wasteful calls of working through the superbasin criterion.
            # Rather than checking each time a process is seen more than Nf times, it is checked
            # when a process is seen more than (2^sb_check_count)*Nf times
            # with sb_check_count starting at 0 and increasing
            # by one each time the superbasin criterion fails
            # In order to keep track of it, it will be written to disk, along with "num_rate_changes".
            # "num_rate_changes" keeps up with how many times barriers were raised in the entire simulation.
        if not os.path.isfile(os.path.join(self.path,"askmc_data.txt")):
            sb_check_count = 0
            num_rate_changes = 0
        else:
            fi = open(os.path.join(self.path,"askmc_data.txt"),"r")
            lines = fi.readlines()
            sb_check_count = int(lines[1].strip().split()[-1])
            num_rate_changes = int(lines[2].strip().split()[-1])
        return sb_check_count, num_rate_changes

    def save_askmc_metadata(self, sb_check_count, num_rate_changes):
        """ Save the current values of the AS-KMC data. """
        fo = open(os.path.join(self.path,"askmc_data.txt"),"w")
        fo.write("[Info for the Chatterjee & Voter AS-KMC method]\n")
        fo.write("sb_check_count = %d\n" % (sb_check_count))
        fo.write("num_rate_changes = %d\n" % (num_rate_changes))

    def get_real_process_table(self, current_state):
        """ Return the real process table. """
        proctable_path = os.path.join(current_state.path,"processtable")
        fi = open(proctable_path)
        lines = fi.readlines()
        fi.close()
        procs = {}
        for l in lines[1:]:
            l = l.strip().split()
            procs[int(l[ID])] = {"saddle_energy":     float(l[ENERGY]), 
                                 "prefactor":         float(l[PREFACTOR]), 
                                 "product":           int  (l[PRODUCT]), 
                                 "product_energy":    float(l[PRODUCT_ENERGY]), 
                                 "product_prefactor": float(l[PRODUCT_PREFACTOR]), 
                                 "barrier":           float(l[BARRIER]), 
                                 "rate":              float(l[RATE]), 
                                 "repeats":           int  (l[REPEATS])}
        return procs

    def get_modified_process_table(self, current_state):
        """ Return the table of modified processes. If it doesn't exist yet, it's hopefully because the system is in the first state.
            These will be "substituted" in place of their corresponding rates in the normal rate table. """
        mod_proctable_path = os.path.join(current_state.path,"askmc_processtable")
        if not os.path.isfile(mod_proctable_path):
            return {}
        fi = open(mod_proctable_path)
        lines = fi.readlines()
        fi.close()
        procs = {}
        for l in lines[1:]:
            l = l.strip().split()
            procs[int(l[ID])] = {"saddle_energy":     float(l[ENERGY]), 
                                 "prefactor":         float(l[PREFACTOR]), 
                                 "product":           int  (l[PRODUCT]), 
                                 "product_energy":    float(l[PRODUCT_ENERGY]), 
                                 "product_prefactor": float(l[PRODUCT_PREFACTOR]), 
                                 "barrier":           float(l[BARRIER]), 
                                 "rate":              float(l[RATE]), 
                                 "view_count":        int  (l[REPEATS])}
        return procs

    def save_modified_process_table(self, current_state, current_state_mod_procs):
        """ Write the modified process table for the current state to disk. """
        mod_proctable_path = os.path.join(current_state.path,"askmc_processtable")
        fo = open(mod_proctable_path,"w")
        fo.write(mod_processtable_header)
        for id in current_state_mod_procs.keys():
            proc = current_state_mod_procs[id]
            fo.write(processtable_line % (id, 
                                         proc['saddle_energy'], 
                                         proc['prefactor'], 
                                         proc['product'], 
                                         proc['product_energy'],
                                         proc['product_prefactor'], 
                                         proc['barrier'],
                                         proc['rate'],
                                         proc['view_count']))
        fo.close()

    def append_modified_process_table(self, current_state, process_id, saddle_energy, prefactor, product, product_energy, product_prefactor, barrier, rate, view_count):
        """ Append a single line to the modified process table on disk. """
        mod_proctable_path = os.path.join(current_state.path,"askmc_processtable")
        # If the file doesn't exist yet, save a ready copy with the header.
        if not os.path.isfile(mod_proctable_path):
            self.save_modified_process_table(current_state, {})
        fo = open(mod_proctable_path, 'a')
        fo.write(processtable_line % (process_id, saddle_energy, prefactor, product, product_energy, product_prefactor, barrier, rate, view_count))
        fo.close()

    def register_transition(self, current_state, next_state):
        """ Whenever there is a move (in KMC), update the view_count, and potentially
            lower rate constants and raise the corresponding transition state energies. """
        # If for some reason, there wasn't actually a move, don't do anything.
        if current_state == next_state:
            return
        sb_check_count, num_rate_changes = self.get_askmc_metadata()
        current_state_mod_procs = self.get_modified_process_table(current_state)
        # Determine if the process is new -- Try to find the process_id in the modified process table.
        next_state_process_id = None
        for process_id in current_state_mod_procs.keys():
            if current_state_mod_procs[process_id]["product"] == next_state.number:
                next_state_process_id = process_id
                break
        # If we've never been along this path before, add it to our modified list
        if next_state_process_id == None:
            # Find the find the process id from the real process table
            current_state_real_procs = self.get_real_process_table(current_state)
            for process_id in current_state_real_procs.keys():
                if current_state_real_procs[process_id]["product"] == next_state.number:
                    next_state_process_id = process_id
                    break
            # Get the info from the actual process table
            procs = current_state_real_procs[next_state_process_id]
            saddle_energy = procs["saddle_energy"]
            prefactor = procs["prefactor"]
            product = procs["product"]
            product_energy = procs["product_energy"]
            product_prefactor = procs["product_prefactor"]
            barrier = procs["barrier"]
            rate = procs["rate"]
            self.append_modified_process_table(current_state, next_state_process_id, saddle_energy, prefactor, product, product_energy, product_prefactor, barrier, rate, 1)
        # Otherwise it's been seen before, and one simply needs to be added to the view_count
        else:
            current_state_mod_procs[next_state_process_id]["view_count"] += 1
            self.save_modified_process_table(current_state, current_state_mod_procs)
            # And if it's been seen enough, check for raising the barriers
            # in the potential superbasin
            if current_state_mod_procs[next_state_process_id]["view_count"] >= (2**sb_check_count)*Nf:
                self.raiseup(current_state, next_state, sb_check_count, num_rate_changes)

    def in_array(self, test, array):
        """ Determine whether two arrays are equivalent.
            Because of the use of numpy, the natural python 'in' test does not work properly.  So this is a workaround.
            "test" should be a 1Xn (1X2) list, and "array" should be a mXn (mX2) array. """
        test = numpy.array(test)
        testvar = 0
        for i in array:
            if numpy.array_equal(test, i):
                testvar = 1
                break
        return testvar

    def is_equal(self, a, b):
        """ Determine whether two floats are 'close'. """
        if abs(a - b) < 1e-5:
            return True
        else:
            return False
    
    def locsearch(self, current_state, origEtrans):
        """ Act recursively to find if the superbasic criterion is met.
            However, ---Note--- that in this implementation, not all neighbors are necessarily checked --
            just those which have been seen so far (which is *probably* all low barrier processes in a superbasin).
            origEtrans should be transition state energy (eV) of the process initially used for the call.
            Immediately before each call, welltest should be set to 1 and edgelist should be any 2X1 numpy array. """
        # "welltest" will serve as a flag to stop the search if it has failed.
        # A value of 1 will indicate it has not yet failed.
        global welltest
        # "edgelist" is the list of edges that have been examined.  It is global so that 
        # other copies of this function do not examine the same edges.
        global edgelist
        if welltest == 1:
            current_state_mod_procs = self.get_modified_process_table(current_state)
            # scan all the neighbor states
            for next_state_id in current_state_mod_procs.keys():
                next_state_num = current_state_mod_procs[next_state_id]["product"]
                if welltest == 1:
                    # If this process has not already been traversed (either direction),
                    # and the barrier is considered "low", its number of sightings (view_count),
                    # in both the forward and backward direction will be checked.
                    if not (self.in_array([current_state.number, next_state_num], edgelist) or self.in_array([next_state_num, current_state.number], edgelist)) \
                        and current_state_mod_procs[next_state_id]["saddle_energy"] < origEtrans + math.log(gamma)/self.Beta:
                            next_state = self.states.get_state(next_state_num)
                            next_state_mod_procs = self.get_modified_process_table(next_state)
                            # Try to find the "process_id" of the current state relative to the next state
                            current_state_id = None
                            for process_id in next_state_mod_procs.keys():
                                if next_state_mod_procs[process_id]["product"] == current_state.number:
                                    current_state_id = process_id
                                    break
                            # If the number of sightings is below the cut-off, the superbasin criterion fails.
                            # Both forward and backward reaction counts are checked.
                            if current_state_mod_procs[next_state_id]["view_count"] < Nf or current_state_id == None or next_state_mod_procs[current_state_id]["view_count"] < Nf:
                                welltest = 0
                            # Otherwise, add this process to "edgelist" to note it's been viewed, and continue the search
                            else:
                                edgelist = numpy.vstack((edgelist,[current_state.number, next_state_num]))
                                self.locsearch(next_state, origEtrans)
    
    def raiseup(self, current_state, next_state, sb_check_count, num_rate_changes):
        """ Determine (with the aid of locsearch) if a superbasin is present.
            If a superbasin is found to be present, raise the rate constants
            and lower the saddle energies and the barriers. """
        # Preparing for the "locsearch" function, "welltest" and "edgelist" are set globally.
        global welltest
        global edgelist
        
        logger.info('Raising barrier between states %d and %d' % (current_state.number, next_state.number))

        welltest = 1
        edgelist = numpy.array([0,0])
        sb_check_count += 1
        current_state_mod_procs = self.get_modified_process_table(current_state)
        # Find the "process_id" of the next state
        for process_id in current_state_mod_procs.keys():
            if current_state_mod_procs[process_id]["product"] == next_state.number:
                next_state_id = process_id
                break
        origEtrans = current_state_mod_procs[next_state_id]["saddle_energy"]
        # Perform "locsearch" to determine if the current state is in a superbasin,
        # and if so, the "bottom" of edgelist will be the contained states
        self.locsearch(current_state, origEtrans)
        if welltest:
            edgelist = edgelist[1:,:]
            # Reset the check count, because a raise has been performed
            sb_check_count = 0
            # Performing adjustments
            for state_pair in edgelist:
                # The state numbers
                state_a_num = state_pair[0]
                state_b_num = state_pair[1]
                # The state objects
                state_a = self.states.get_state(state_a_num)
                state_b = self.states.get_state(state_b_num)
                # The state process tables
                state_a_mod_procs = self.get_modified_process_table(state_a)
                state_b_mod_procs = self.get_modified_process_table(state_b)
                # The state energies
                state_a_energy = state_a.get_energy()
                state_b_energy = state_b.get_energy()
                # And the state process id's from the other's perspective
                for process_id in state_a_mod_procs.keys():
                    if state_a_mod_procs[process_id]["product"] == state_b_num:
                        state_b_id = process_id
                        break
                for process_id in state_b_mod_procs.keys():
                    if state_b_mod_procs[process_id]["product"] == state_a_num:
                        state_a_id = process_id
                        break
                # The new rates
                a_b_new_rate = state_a_mod_procs[state_b_id]["rate"]/alpha
                b_a_new_rate = state_b_mod_procs[state_a_id]["rate"]/alpha
                # The new saddle energies. Both calculated then compared for assurance
                a_b_new_saddle = math.log(a_b_new_rate/state_a_mod_procs[state_b_id]["prefactor"])/(-self.Beta) + state_a_energy
                b_a_new_saddle = math.log(b_a_new_rate/state_b_mod_procs[state_a_id]["prefactor"])/(-self.Beta) + state_b_energy
                if not self.is_equal(a_b_new_saddle, b_a_new_saddle):
                    # NOTE - this exception is primarily for ensuring proper functioning of the method.
                    # If it's never raised, then only one of the above saddles needs to be calculated,
                    # and this "if" clause may be removed. (Note that below, *_*_new_saddle must then be replaced)
                    raise ValueError("When recalculating, saddle energies from changed rate constants,\
                                     different saddle energies were obtained from the two directions!")
                # The new "barrier" values.
                a_b_new_barrier = a_b_new_saddle - state_a_energy
                b_a_new_barrier = b_a_new_saddle - state_b_energy
                # Saving the new data
                state_a_mod_procs[state_b_id]["rate"] = a_b_new_rate
                state_b_mod_procs[state_a_id]["rate"] = b_a_new_rate
                state_a_mod_procs[state_b_id]["saddle_energy"] = a_b_new_saddle
                state_b_mod_procs[state_a_id]["saddle_energy"] = b_a_new_saddle
                state_a_mod_procs[state_b_id]["barrier"] = a_b_new_barrier
                state_b_mod_procs[state_a_id]["barrier"] = b_a_new_barrier
                state_a_mod_procs[state_b_id]["view_count"] = 0
                state_b_mod_procs[state_a_id]["view_count"] = 0
                self.save_modified_process_table(state_a, state_a_mod_procs)
                self.save_modified_process_table(state_b, state_b_mod_procs)
            num_rate_changes += 1
        # Finally, save the 'tallies' being kept track of
        self.save_askmc_metadata(sb_check_count, num_rate_changes)
