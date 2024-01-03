import os
from jarvis.core.atoms import Atoms as JarvisAtoms
from jarvis.core.atoms import ase_to_atoms
from ase.io import read as ASEread
import matplotlib.pyplot as plt
import numpy as np
from ase.io import vasp


#alignn setup
from alignn.ff.ff import AlignnAtomwiseCalculator,default_path,wt10_path,alignnff_fmult,fd_path,ForceField
#model_path = wt10_path()
model_path=alignnff_fmult() 
calc = AlignnAtomwiseCalculator(path=model_path)


# ALIGNN CALCS

def make_atoms_object(filepath, mode='jarvis'):
    if mode == 'jarvis':
        atoms = JarvisAtoms.from_poscar(filename=filepath)
    elif mode == 'ase':
        atoms = ASEread(filename=filepath)
    return atoms


# OPTIMIZE LATTICE


def optimize_lattice(atoms):
    '''
    Optimizes the lattice structure of a POSCAR file using the specified alignn-ff model

    Inputs:
      jarvis atoms object

    Returns:
      opt: optimized lattice structure (jarvis.core.atoms.Atoms object)

    '''

    
    # run alignn-ff on the specified atom system and predict a forcefield

    ff = ForceField(
        jarvis_atoms=atoms,
        model_path=model_path,
        stress_wt=0.3,
        force_multiplier=1,
        force_mult_natoms=False,
    )

    # optimize lattice structure by minimizing energy

    opt, en, fs = ff.optimize_atoms()  # logfile=None)

    return opt


def energy_per_atom(atoms):
    '''
    Calculates the energy per atom and volume of a cystal for a POSCAR file using the specified alignn-ff model

    Inputs:
      atoms: atoms object (Jarvis)

    Returns:
      energy_per_atom: total lattice energy divided by number of atoms (float)
    '''

    num_atoms = atoms.num_atoms


    # ALIGNN-FF object
    ff = ForceField(
      jarvis_atoms=atoms,
      model_path=model_path,
      stress_wt=0.3,
      force_multiplier=1,
      force_mult_natoms=False,
    )

    # get potential energy of unrelaxed atoms
    PE, fs = ff.unrelaxed_atoms()

    energy_per_atom = PE/num_atoms
    #print(energy_per_atom)
    return energy_per_atom


def calculate_energy(filepath, relaxation=False):

    atoms = make_atoms_object(filepath)
    energy = 0
    vasp_data = None

    if relaxation:
        relaxed_atoms=optimize_lattice(atoms)
        energy = energy_per_atom(relaxed_atoms)
        temp_filename = 'vasp_files_temp/relaxed_lattice.vasp'
        JarvisAtoms.write_poscar(relaxed_atoms, filename=temp_filename)
        with open(temp_filename, 'r') as file:
            vasp_data = file.readlines()

    else:
        energy = energy_per_atom(atoms)
    
    return energy, vasp_data


if __name__ == '__main__':

    filepaths = ['vasp_files_temp/AlFe_FCC.vasp']

    calculate_energy(filepaths[0],relaxation=True)