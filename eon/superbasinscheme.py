##-----------------------------------------------------------------------------------
## eOn is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## A copy of the GNU General Public License is available at
## http://www.gnu.org/licenses/
##-----------------------------------------------------------------------------------

import os
import logging
logger = logging.getLogger('superbasinscheme')

import config

import sys
if sys.version_info < (2, 6):
    mpsuperbasin = None
else:
    import mpsuperbasin

import superbasin

class SuperbasinScheme:
    ''' This poorly-named class handles keeping track of which states belong
        to which superbasins, the SuperBasin object of those superbasins, and
        superbasining criteria. It also expands and merges superbasins'''

    def __init__(self, superbasin_path, states, kT):

        if config.sb_use_arbitrary_precision:
            if mpsuperbasin is None:
                print "Was unable to import mpsuperbasin; is mpmath installed?"
#                import sys
                sys.exit()
            global superbasin
            superbasin = mpsuperbasin

        self.path = superbasin_path
        self.path_storage = superbasin_path + "storage/"

        self.states = states
        self.kT = kT

        if not os.path.isdir(self.path):
            logger.warning('Superbasin path does not exist, creating %s' % self.path)
            os.makedirs(self.path)
            os.makedirs(self.path_storage)

        self.superbasins = []
        dirs = os.listdir(self.path)
        self.next_sb_num = 0
        for i in dirs:
            if i != 'storage':

                self.next_sb_num = max(self.next_sb_num, int(i))
                self.superbasins.append(superbasin.Superbasin(self.path, i, get_state = states.get_state))

        self.next_sb_num += 1
        self.read_data()

    def get_containing_superbasin(self, state):
        for i in self.superbasins:
            if i.contains_state(state):
                return i
        return None

    def make_basin(self, merge_states):

        # is there an upper limit for the size of a superbasin
        if config.sb_max_size:
            # first determine how many states will be in the new superbasin
            numstates = 0
            for i in merge_states:
                sb = self.get_containing_superbasin(i)
                if sb is None:
                    numstates += 1
                else:
                    numstates += len(sb.states)
            # if number of states in the new superbasin wil be larger than 2, do not proceed:
            if numstates > config.sb_max_size:
                return
        
        new_sb_states = []
        for i in merge_states:
            sb = self.get_containing_superbasin(i)
            if sb is None:
                if i not in new_sb_states:
                    new_sb_states.append(i)
            else:
                for j in sb.states:
                    if j not in new_sb_states:
                        new_sb_states.append(j)
                # keep basins to analyze data
                if 1:
                    sb.delete(self.path_storage)
                else:
                    sb.delete()

                self.superbasins.remove(sb)

        self.states.connect_states(new_sb_states) #XXX:This should ensure detailed balance
        # However, it will likely be very slow. We should be able to do without it.
        # Also, if confidence is changed and new processes are found, the superbasin
        # will ignore these new processes.

        self.superbasins.append(superbasin.Superbasin(self.path, self.next_sb_num, state_list = new_sb_states)) 

        logger.info("Created superbasin with states " + str([i.number for i in new_sb_states]))
        self.next_sb_num += 1

    def register_transition(self, start_state, end_state):
        raise NotImplementedError()

    def write_data(self):
        raise NotImplementedError()

    def read_data(self):
        raise NotImplementedError()

    def __del__(self):
        self.write_data()
    #def get_superbasins(self):
    #    if self.superbasins is not None:
    #        return self.superbasins
    #    else:
    #        dirs = os.listdir(self.path)
    #        for i in dirs:
    #            path = os.path.join(self.path, i)
    #            self.superbasins[int(i)] = superbasin.Superbasin(path)


class TransitionCounting(SuperbasinScheme):
    ''' Implements the transition counting scheme for superbasin detection '''

    def __init__(self, superbasin_path, states, kT, num_transitions):
        self.num_transitions = num_transitions
        SuperbasinScheme.__init__(self,superbasin_path, states, kT)

    def register_transition(self, start_state, end_state):
        logger.debug('Registering transitions')

        if start_state == end_state and not config.comp_use_identical:
#        if start_state == end_state:
            return

        start_count = self.get_count(start_state)
        if end_state not in start_count:
            start_count[end_state] = 0
        start_count[end_state] += 1

        if start_count[end_state] >= self.num_transitions:
            logger.debug( "Making basin ....")
            self.make_basin([start_state, end_state])

    def write_data(self):
        logger.debug('writing')
        for start_state in self.count:
            data_path = os.path.join(start_state.path, config.sb_state_file)
            f = open(data_path, 'w')
            for end_state in self.count[start_state]:
                print >> f, end_state.number, self.count[start_state][end_state]
            f.close()

    def read_data(self):
        self.count = {}

    def get_count(self, state):
        try:
            return self.count[state]
        except:
            data_path = os.path.join(state.path, config.sb_state_file)
            self.count[state] = {}
            if os.path.isfile(data_path):
                f = open(data_path, 'r')
                for i in f:
                    i = i.strip().split()
                    self.count[state][self.states.get_state(int(i[0]))] = int(i[1]) 
                f.close()
            return self.count[state]


class EnergyLevel(SuperbasinScheme):

    def __init__(self, superbasin_path, states, kT, energy_increment):
        self.energy_increment = energy_increment
        self.levels = {}
        SuperbasinScheme.__init__(self,superbasin_path, states, kT)

    def get_energy_increment(self, e_min, e_global_min, e_saddle):
        return self.energy_increment * (e_saddle - e_min) / (e_saddle - e_global_min)

    def get_statelist(self, state):
        sb = self.get_containing_superbasin(state)
        if sb:
            return sb.states
        else:
            return [ state ]

    # start_state and end_state are the non-sb ids. 
    def register_transition(self, start_state, end_state):
        '''Increments the energy level of the end state or sets it equal to the energy
           of the end_state if it hasn't been visited before.'''

        # error
        if start_state == end_state and not config.comp_use_identical:
        #if start_state == end_state:
            return

        # if the start state does not have an energy level yet, we set it to the energy of the state.
        if start_state not in self.levels:
            self.levels[start_state] = start_state.get_energy()

        # if the end state does not have an energy level yet, set it to the energy of the state.
        if end_state not in self.levels:
            self.levels[end_state] = end_state.get_energy()

        # determine wheter or not the start and end states belong to a superbasin.
        # if they belong to a superbasin, we need to know the ids of the states inside
        # that superbasin to determine the minimum energy state inside the superbasin.

        start_statelist = self.get_statelist(start_state)
        end_statelist   = self.get_statelist(end_state)

        e_min        = min ( state.get_energy() for state in end_statelist )
        e_global_min = min ( e_min , ( state.get_energy() for state in start_statelist ) )

        # determine the barrier
        # (LJ: What happens if there is more then one path between start_state and end_state???)
        barrier = 1e200
        proc_tab = start_state.get_process_table()
        for key in proc_tab:
            if proc_tab[key]['product'] == end_state.number:
                barrier = min(proc_tab[key]['barrier'], barrier)

        if barrier > 1e199:
            logger.warning("Start and end state have no direct connection")
            return
        saddle_energy = barrier + start_state.get_energy()

        # increment the level of the end_state. 
        for i in end_statelist:
            self.levels[i] += self.get_energy_increment(e_min, e_global_min, saddle_energy)

        # merge states if one of the two levels is higher than the saddle energy
        largest_level = max(self.levels[start_state], self.levels[end_state])

        if largest_level > saddle_energy:
            self.levels[start_state] = largest_level 
            self.levels[end_state] = largest_level 
            for i in end_statelist: #this may also be just [ end_state ]
                self.levels[i] = largest_level
            self.make_basin([start_state, end_state])

    def read_data(self):
        logger.debug('reading')
        for i in range(self.states.get_num_states()):
            state = self.states.get_state(i)
            data_path = os.path.join(state.path, config.sb_state_file)
            if os.path.isfile(data_path):
                f = open(data_path, 'r')
                self.levels[self.states.get_state(i)] = float(f.read().strip())
                f.close()

    def write_data(self):
        logger.debug('writing')
        for i in self.levels:
            data_path = os.path.join(i.path, config.sb_state_file)
            f = open(data_path, 'w')
            print >> f, "%f\n" % self.levels[i]
            f.close()

