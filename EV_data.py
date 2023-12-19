import os
from jarvis.core.atoms import Atoms as JarvisAtoms
from jarvis.core.atoms import ase_to_atoms
from ase.io import read as ASEread
import numpy as np
from ase.io import vasp


# choose alignn-ff model

#model_path=wt10_path()
model_path=alignnff_fmult()


def sort_lists_by_x(x, y):
    # Pair and sort the data by x values
    data = sorted(zip(x, y), key=lambda item: item[0])
    x_sorted, y_sorted = zip(*data)
    return list(x_sorted), list(y_sorted)


def find_lowest_energy(FCC, BCC):
    """
    Compare two lists and identify which one contains the lowest value.

    Parameters:
    - FCC (list): The FCC list.
    - BCC (list): The BCC list.

    Returns:

    """
    Fmin = min(FCC, default=float('inf'))
    Bmin = min(BCC, default=float('inf'))

    if Fmin < Bmin:
        return 'FCC'
    elif Bmin<Fmin:
        return 'BCC'
    else:
        return 'Equal'

def energy_calc(atoms):
    '''
    Calculates the energy per atom of a cystal for a POSCAR file using the specified alignn-ff model

    Inputs:
      atoms: jarvis atoms object 

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

    return energy_per_atom


def change_lattice_parameter(atoms, lattice_parameter, crystal_type):
    """
    Change the lattice parameter of an atoms object

    Returns:
    ase atoms object, volume of unit cell
    """


    # Set cell parameters based on the test structure type
    if crystal_type == 'FCC':
        atoms.set_cell([lattice_parameter, lattice_parameter, lattice_parameter])
        volume = lattice_parameter**3

    elif crystal_type == 'BCC':
        atoms.set_cell([lattice_parameter, lattice_parameter, lattice_parameter*2])
        volume = lattice_parameter*lattice_parameter*(lattice_parameter*2)

    else:
        print(':(')



    return atoms, volume

def EV_data(file):
    """
    Calculate EV data for polymorphs of alloy

    inputs: file (str)

    returns: EV_data (dict)
    """

    # change the lattice parameter list between FCC/BCC such that they are centered around the same volume 

    if 'FCC' in file:
        test_structure = 'FCC'
        lattice_parameter_list= [4,5,6,7,8,9]
    elif 'BCC' in file:
        test_structure = 'BCC'
        lattice_parameter_list= [4,5,6,7,8,9]
    
    volumes = []
    energies = []
    ase = ASEread(file)

    # calculate individual energy points
    for param in lattice_parameter_list:

        atoms, vol = change_lattice_parameter(ase, param, test_structure)
        jarvis = ase_to_atoms(atoms)
        energy = energy_calc(jarvis)
        volumes.append(vol)
        energies.append(energy)


    volumes, energies = sort_lists_by_x(volumes,energies)

    EV_data = {key: value for key, value in zip(volumes, energies)}

    return EV_data



