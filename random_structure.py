from pymatgen.core import Lattice, Structure
from jarvis.core.atoms import pmg_to_atoms
from ase.spacegroup import crystal
from alloy_mol_fractions import find_mole_fractions


'''
from pyxtal import pyxtal
import re
'''

def jvs_from_pmg_disordered_structure(composition, crystal): 


    '''
    create a disordered pymatgen structure with a specified crystal structure
    inputs: 
    composition: dict
    crystal: str ('FCC' or 'BCC')

    outputs: 
    JARVIS atoms structure
    '''
    spacegroup = 'Fm-3m'

    if crystal == 'FCC':
        spacegroup = 'Fm-3m'
    else:
        spacegroup = 'Fm-3m'


    # create a disordered V-Co-Ni FCC structure
    structure = Structure.from_spacegroup(
        spacegroup,
        lattice=Lattice.cubic(3.58),
        species=[composition],
        coords=[[0, 0, 0]])

    jvs = pmg_to_atoms(structure)

def supercell_from_ase(alloy, crystal):

    composition = find_mole_fractions(alloy)
    elements = list(composition.keys())
    spacegroup = 225

    if crystal == 'FCC':
        spacegroup = 225
        size = [6, 2, 2]
    else:
        spacegroup = 229
        size = [10, 5, 5]


    structure = crystal(elements, spacegroup=spacegroup, size=size)

'''
def random_structure(alloy, crystal):
    
    # makes structure of a given composition, number of atoms, and crystal structure using pyxtal

    # returns JARVIS atoms


    # crystal string converted to spacegroup number
    spacegroup = 225

    if crystal == 'FCC':
        spacegroup = 225
    else:
        spacegroup = 225

    # regular expression to extract alloying elements from equiatomic alloys
    elements = re.findall(r'[A-Z][a-z]*', alloy)

    # random pyxtal structure (40 atoms with spacegroup determined by crystal specified
    structure = pyxtal()
    structure.from_random(3, 225, elements, [8,8,8,8,8])
    pmg = structure.to_pymatgen()
    jvs = pmg_to_atoms(pmg)
    return jvs
'''


if __name__ =='main':
    '''
    alloy = 'FeCrCuNi'
    composition = {"V": 1.0/3.0, "Co": 1.0/3.0, "Ni": 1.0/3.0}
    atoms = jvs_from_pmg_disordered_structure(composition, 'FCC')
    print(atoms)
    '''

    ase = supercell_from_ase(alloy, 'FCC')
    print(ase)
    '''
    jvs = random_structure('FeNiCuTiSi', 'FCC')
    print(f'pyxtal{jvs}')
    ''' 

    