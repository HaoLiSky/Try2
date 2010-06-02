""" The atoms module. """

import numpy
import logging
logger = logging.getLogger('atoms')
#TODO: Add list of covalent radii from tsse/jmol/kdb. (Rye can do)



class Atoms:
    """ The Atoms class. """

    def __init__(self, n_atoms):
        self.r = numpy.zeros((n_atoms,3))
        self.free = numpy.ones(n_atoms)
        self.box = numpy.zeros((3,3))
        self.names = ['']*n_atoms

    def __len__(self):
        return len(self.r)
        
    def copy(self):
        p = Atoms(len(self))
        p.r = self.r.copy()
        p.free = self.free.copy()
        p.box = self.box.copy()
        p.names = self.names[:]
        return p
        


def pbc(r, box, ibox = None):
    """
    Applies periodic boundary conditions.
    Parameters:
        r:      the vector the boundary conditions are applied to
        box:    the box that defines the boundary conditions
    """
    if ibox == None:    
        ibox = numpy.linalg.inv(box)
    vdir = numpy.dot(r, ibox)
    vdir = (vdir % 1.0 + 1.5) % 1.0 - 0.5
    return numpy.dot(vdir, box)
    


def per_atom_norm(v, box, ibox = None):
    diff = pbc(v, box, ibox)
    return numpy.array([numpy.linalg.norm(d) for d in diff])



def identical(atoms1, atoms2, epsilon_r):
    #TODO: Custom comparator could be MUCH better
    if len(atoms1) != len(atoms2):
        return False
    
    for i in range(3):
        for j in range(3):
            #XXX: Hardcoded comparison criteria
            if abs(atoms1.box[i][j] - atoms2.box[i][j]) > .0001:
                logger.warning("Identical returned false because boxes were not the same")
                return False

    def sortr(named_r, epsilon_r, box, axis = 0):
        #we need to sort our atom identities along with coordinates
        if len(named_r) ==1:
            return named_r
        sr = sorted(named_r, key = lambda foo: foo[axis])
        brackets = []
        bracket = []
        #partition sorted x list into 
        for i in sr:
            if len(bracket) > 0:
                #XXX: Suboptimal
                v2 = numpy.zeros(3)
                v1 = numpy.zeros(3)

                v2[axis] = i[axis]
                v1[axis] = bracket[-1][axis]
                if numpy.linalg.norm(pbc(v2 - v1, box)) > epsilon_r:
                    brackets.append(bracket)
                    bracket = []
            bracket.append(i)
        if len(bracket) > 0:
            brackets.append(bracket)

        sorted_bracket_list = []
        for i in brackets:
            if axis + 1 <= 2:
                i = sortr(i, epsilon_r, box, axis = axis + 1)
            elif len(i) > 1:
                logger.warning('Identical found two atoms with the "same" coordinates')
            sorted_bracket_list.append(i)

        return sum(sorted_bracket_list, [])

    named_r1 = [(list(atoms1.r[i]) + [atoms1.names[i]]) for i in range(len(atoms1))]
    named_r2 = [(list(atoms2.r[i]) + [atoms2.names[i]]) for i in range(len(atoms2))]
    sorted_r1 = sortr(named_r1, epsilon_r, atoms1.box)
    sorted_r2 = sortr(named_r2, epsilon_r, atoms1.box)
    
    #construct names and comparison vectors
    v = numpy.zeros((len(atoms1), 3))
    for i in range(len(v)):
        v[i] = sorted_r1[i][0:3]
        v[i] -= sorted_r2[i][0:3] 
        
        #compare names
        if sorted_r1[i][3] != sorted_r2[i][3]:
            return False

    for i in per_atom_norm(v, atoms1.box):
        if i > epsilon_r:
            return False

    return True






    



def sweep_and_prune(p_in, cutoff, strict = True, bc = True):
    """ Returns a list of nearest neighbors within cutoff for each atom. 
        Parameters:
            p_in:   Atoms object
            cutoff: the radius within which two atoms are considered to intersect.
            strict: perform an actual distance check if True
            bc:     include neighbors across pbc's """
    #TODO: Get rid of 'cutoff' and use the covalent bond radii. (Rye can do)
    # Do we want to use covalent radii? I think the displace class wants to allow for user-defined cutoffs.
        # We should have both options available. -Rye
    #TODO: Make work for nonorthogonal boxes.
    p = p_in.copy()
    p.r = pbc(p.r, p.box)
    p.r -= numpy.array([min(p.r[:,0]), min(p.r[:,1]), min(p.r[:,2])]) 
    numatoms = len(p)
    coord_list = []
    for i in range(numatoms):
        coord_list.append([i, p.r[i]])
    sorted_x = sorted(coord_list, key = lambda foo: foo[1][0])
    intersect_x = []
    for i in range(numatoms):
        intersect_x.append([])
    for i in range(numatoms):
        done = False
        j = i + 1
        if not bc and j >= numatoms:
            done = True
        while not done:
            j = j % numatoms
            dist = abs(sorted_x[j][1][0] - sorted_x[i][1][0])
            if p.box[0][0] - sorted_x[i][1][0] < cutoff:
                dist = min(dist, (p.box[0][0] - sorted_x[i][1][0]) + sorted_x[j][1][0])
            if dist < cutoff:
                intersect_x[sorted_x[i][0]].append(sorted_x[j][0]) 
                intersect_x[sorted_x[j][0]].append(sorted_x[i][0]) 
                j += 1
                if not bc and j >= numatoms:
                    done = True
            else:
                done = True
    sorted_y = sorted(coord_list, key = lambda foo: foo[1][1])
    intersect_y = []
    for i in range(numatoms):
        intersect_y.append([])
    for i in range(numatoms):
        done = False
        j = i + 1
        if not bc and j >= numatoms:
            done = True
        while not done:
            j = j % numatoms
            dist = abs(sorted_y[j][1][1] - sorted_y[i][1][1])
            if p.box[1][1] - sorted_y[i][1][1] < cutoff:
                dist = min(dist, (p.box[1][1] - sorted_y[i][1][1]) + sorted_y[j][1][1])
            if dist < cutoff:
                intersect_y[sorted_y[i][0]].append(sorted_y[j][0]) 
                intersect_y[sorted_y[j][0]].append(sorted_y[i][0]) 
                j += 1
                if not bc and j >= numatoms:
                    done = True
            else:
                done = True
    sorted_z = sorted(coord_list, key = lambda foo: foo[1][2])
    intersect_z = []
    for i in range(numatoms):
        intersect_z.append([])
    for i in range(numatoms):
        done = False
        j = i + 1
        if not bc and j >= numatoms:
            done = True
        while not done:
            j = j % numatoms
            dist = abs(sorted_z[j][1][2] - sorted_z[i][1][2])
            if p.box[2][2] - sorted_z[i][1][2] < cutoff:
                dist = min(dist, (p.box[2][2] - sorted_z[i][1][2]) + sorted_z[j][1][2])
            if dist < cutoff:
                intersect_z[sorted_z[i][0]].append(sorted_z[j][0]) 
                intersect_z[sorted_z[j][0]].append(sorted_z[i][0]) 
                j += 1
                if not bc and j >= numatoms:
                    done = True
            else:
                done = True
    intersect = []
    for i in range(numatoms):
        intersect.append([])
        intersect[i] = list(set(intersect_x[i]).intersection(intersect_y[i]).intersection(intersect_z[i]))
    if strict:
        ibox = numpy.linalg.inv(p.box)
        for i in range(numatoms):
            l = intersect[i][:]
            for j in l:
                dist = numpy.linalg.norm(pbc(p.r[i] - p.r[j], p.box, ibox))
                if dist > cutoff:
                    intersect[i].remove(j)
                    intersect[j].remove(i)
    return intersect
    

    
def coordination_numbers(p, cutoff):
    """ Returns a list of coordination numbers for each atom in p """
    nl = sweep_and_prune(p, cutoff)
    return [len(l) for l in nl]
    


def least_coordinated(p, cutoff):
    """ Returns a list of atom indices in p with the lowest coordination numbers """
    cn = coordination_numbers(p, cutoff)
    mincoord = min(cn)
    least = []
    for i in range(len(cn)):
        if cn[i] <= mincoord:
            least.append(i)
    return least

    
    
    
if __name__ == "__main__":
    import io
    #p = io.loadcon("foo.con")
    #print coordination_numbers(p, 3.0)
    #print least_coordinated(p, 3.0)

    import sys
    logger = logging
    p1 = io.loadcon(sys.argv[1])
    p2 = io.loadcon(sys.argv[2])
    print identical(p1,p2,.01)
