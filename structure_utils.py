from pymatgen.core.structure import Structure
from pymatgen.core.lattice import Lattice
from pymatgen.core.composition import Composition
from pymatgen.core import Species
from pymatgen.core.periodic_table import Element
from pymatgen.symmetry.groups import SpaceGroup

import math
import numpy as np
import logging


def is_stoichiometric(comp: Composition):
    """Check if the composition is stoichiometric (integer proportions or equiatomic). 
    Make sure all of the composition numbers are integers. If they are fractional, that would indicate a percentage
    e.g., Al0.875CoCrFeNi would be considered as Al being 87.5 and the rest equiatomic
    e.g., Al2CoCrFeNi would be considered as Al being 1 and the rest would be 1, so it would be stoichiometric
    
    Args:
        comp (Composition): Composition to check.  Assumes a pymatgen Composition object.
    
    Returns:
        bool: True if stoichiometric, False otherwise.
    """

    for amt in comp.get_el_amt_dict().values():
        if amt != 1 and not amt.is_integer():
            return False
    return True

from pymatgen.core import Composition

def stoichiometry_to_atom_percent_composition(comp: Composition):
    """
    Convert stoichiometric representation to a Composition object with atom percent composition.
    
    Parameters:
    - comp (Composition): Stoichiometric representation of the compound (e.g., "H2O").
    
    Returns:
    - Composition: A Composition object with elements as keys and their atom percent compositions as values.
    """

    total_atoms = 0    
    # Calculate the total number of atoms
    for el, amt in comp.get_el_amt_dict().items():
        total_atoms += amt

    # Calculate the fractional composition for each element
    fractional_composition = {el: comp[el] / total_atoms for el in comp.elements}
    
    # Create a new Composition object with fractional composition
    new_comp = Composition(fractional_composition)
    
    return new_comp


def adjust_equiatomic_composition(comp: Composition):
    """
    If any of the elements are fractional, adjust all of the others that aren't specified to the equivelent fraction as if
    they were equiatomic. 
    e.g., Al0.875CoCrFeNi would be considered as Al being 87.5 and the rest equiatomic
    e.g., Al2CoCrFeNi would be considered as Al being 1 and the rest would be 1, so it would be stoichiometric
    """
    #TODO: verify that everything adds up to 1'ish
    #TODO: verify that any partial fractional compositions do not add up to be more than 1
    #TODO: make sure every atom gets used at least once...small fractions sometimes omit thos atoms in a smaller supercell

    # Initialize a dictionary to hold the element proportions
    element_proportions = {}
    
    # Check if the composition is already stoichiometric
    if is_stoichiometric(comp):
        # If it is, convert it to a Composition object with atom percent composition
        return stoichiometry_to_atom_percent_composition(comp)
    
    # Total specified proportion (excluding elements assumed to be equiatomic)
    total_specified_proportion = 0
    # Count elements assumed to be equiatomic (initially marked by amount=1 in pymatgen)
    equiatomic_elements_count = 0
    
    for el, amt in comp.get_el_amt_dict().items():
        if amt == 1:
            # Element intended to be equiatomic, count it for now
            equiatomic_elements_count += 1
        else:
            # Element with specified proportion
            total_specified_proportion += amt
            element_proportions[el] = amt
    
    # If there are elements intended to be equiatomic, adjust their proportions
    if equiatomic_elements_count > 0:
        remaining_proportion = 1 - total_specified_proportion
        equiatomic_proportion = remaining_proportion / equiatomic_elements_count
        
        # Update proportions for equiatomic elements
        for el, amt in comp.get_el_amt_dict().items():
            if amt == 1:
                element_proportions[el] = equiatomic_proportion
    
    # Construct the adjusted composition
    adjusted_comp = Composition(element_proportions)
    
    return adjusted_comp

def estimate_lattice_parameter_fcc(average_radius: float):
    """
    For FCC, the lattice parameter is the side of the cube with an atom in the center of the face, and an atom on the corner.
    So, the diagonal across the face is 1/2 atom on the corner, a full atom and another 1/2 atom at the other corner.
    So, 2 atoms across the diagonal of the face.  Solve for the side of the cube:

    Args:
        average_radius: average radius of the atoms in the lattice

    Return:
        lattice parameter of the composition assumming FCC in same units as average_radius
    """
    return average_radius * np.sqrt(2)

def estimate_lattice_parameter_bcc(average_radius: float):
    """
    For BCC, the lattice parameter is the side of a cube with an atom in the middle of the cube, and an atom on the corner.
    So, the diagonal across the interior of the cube is 1/2 atom each corner plus one in the middle, so 2 atoms across the diagonal.
    Solve for the side of the cube:

    Args:
        average_radius: average radius of the atoms in the lattice
    
    Returns:
        lattice parameter of the composition assumming bcc in same units as average_radius
    
    """
    return 2*average_radius / np.sqrt(3)

def get_weighted_average_radius_for_material(comp: Composition):
    atomic_radius = 0.0

    # for each element in a composition, construct an element object and extract its radius
    for element in comp.elements:
        logging.debug(f"{element.symbol} atomic radius is {element.atomic_radius} with atomic fraction {comp.get_atomic_fraction(element)}")
        atomic_radius += element.atomic_radius * comp.get_atomic_fraction(element)

    logging.info(f"Weighted Average Atomic radius for {comp} is {atomic_radius}")
    return atomic_radius

def get_largest_element(comp: Composition):
    max_radius = 0
    for element in comp.elements:
        if element.atomic_radius > max_radius:
            max_radius = element.atomic_radius

    logging.info(f"Maximum Atomic radius for {comp} is {max_radius}")

    return max_radius

def get_most_common_element(comp: Composition):
    comp_dict = comp.to_reduced_dict
    return Element(max(comp_dict, key=comp_dict.get))

def calculate_fcc_scaling_factors(total_atoms):
    """
    Calculate the scaling factors for an FCC structure to achieve a target number of atoms.
    
    Parameters:
    - total_atoms: The target total number of atoms in the supercell.
    
    Returns:
    - A tuple representing the scaling factors (nx, ny, nz) to be used for the supercell.
    """
    
    # Each FCC unit cell contains 4 atoms
    atoms_per_unit_cell = 4
    
    # Calculate the number of unit cells needed to achieve the target number of atoms
    # Since we're aiming for a cubic supercell, we take the cube root of the ratio
    # between the total desired atoms and the atoms per unit cell, and then round it up
    # to the nearest whole number to ensure we meet or exceed the target atom count.
    num_unit_cells = math.ceil((total_atoms / atoms_per_unit_cell) ** (1/3))
    
    # The scaling factors for x, y, and z are the same for a cubic supercell
    return (num_unit_cells, num_unit_cells, num_unit_cells)

def calculate_bcc_scaling_factors(total_atoms):
    """
    Calculate the scaling factors for a BCC structure to achieve a target number of atoms.
    
    Parameters:
    - total_atoms: The target total number of atoms in the supercell.
    
    Returns:
    - A tuple representing the scaling factors (nx, ny, nz) to be used for the supercell.
    """
    
    # Each BCC unit cell contains 2 atoms
    atoms_per_unit_cell = 2
    
    # Calculate the number of unit cells needed to achieve the target number of atoms
    # Since we're aiming for a cubic supercell, we take the cube root of the ratio
    # between the total desired atoms and the atoms per unit cell, and then round it up
    # to the nearest whole number to ensure we meet or exceed the target atom count.
    num_unit_cells = math.ceil((total_atoms / atoms_per_unit_cell) ** (1/3))
    
    # The scaling factors for x, y, and z are the same for a cubic supercell
    return (num_unit_cells, num_unit_cells, num_unit_cells)

def propose_fcc_cutoffs(structure: Structure):
    """
    Propose cutoff values for pairs and triplets in an FCC lattice based on the lattice parameter.
    
    Parameters:
    - structure: Structure: The full FCC structure.
    
    Returns:
    - dict: Dictionary with proposed cutoff values for pairs and triplets.
    """

    # Get the lattice parameter from the structure
    lattice_parameter = structure.lattice.a
    
    # Nearest neighbor (NN) distance
    nn_distance = lattice_parameter / (2**0.5)
    
    # Second nearest neighbor distance is equal to the lattice parameter
    second_nn_distance = lattice_parameter
    
    # Propose cutoffs: For pairs, use the NN distance.
    # For triplets, use the second NN distance to ensure inclusion of these interactions.
    cutoffs = {
        2: nn_distance,  # Pair cutoff
        3: second_nn_distance  # Triplet cutoff
    }
    
    return cutoffs

def propose_bcc_cutoffs(structure: Structure):
    """
    Propose cutoff values for pairs and triplets in a BCC lattice based on the lattice parameter.
    
    Parameters:
    - structure (Structure): The full BCC structure.
  
    Returns:
    - dict: Dictionary with proposed cutoff values for pairs and triplets.
    """
    # Get the lattice parameter from the structure
    lattice_parameter = structure.lattice.a

    # Nearest neighbor (NN) distance
    nn_distance = (lattice_parameter * (3**0.5)) / 2
    
    # Second nearest neighbor distance is equal to the lattice parameter
    second_nn_distance = lattice_parameter
    
    # Propose cutoffs: For pairs, use the NN distance.
    # For triplets, use the second NN distance to ensure inclusion of these interactions.
    cutoffs = {
        2: nn_distance,  # Pair cutoff
        3: second_nn_distance  # Triplet cutoff
    }
    
    return cutoffs


def create_random_supercell_structure(composition: Composition, crystal: str, total_atoms=100 ):

    valid_crystal_types = {"fcc", "bcc"}

    # convert crystal to lower and compare to list of valid crystal types
    crystal = crystal.lower()

    # Check that the crystal type is valid, if not log an error and raise an exception
    assert crystal in valid_crystal_types, f"{crystal} is not a valid crystal type. Valid crystal types are {', '.join(valid_crystal_types)}."

    # use the most common element as the basis for a creating a unary crystal structure.  Could also use the largest.
    el = get_most_common_element(composition)

    # ---- Make a unit cell of just one element type and scale it up to total_atoms -----
    if crystal == "fcc":
        a = estimate_lattice_parameter_fcc(el.atomic_radius)
        
        # Create FCC structure using space group Fm-3m (225)
        structure = Structure.from_spacegroup("Fm-3m", Lattice.cubic(a), [el.name], [[0, 0, 0]])

        scaling_factors = calculate_fcc_scaling_factors(total_atoms)
        print(f"Scaling factors for FCC structure to achieve ~{total_atoms} atoms: {scaling_factors}")
        supercell = structure.make_supercell(scaling_factors)

    elif crystal == "bcc":
        a = estimate_lattice_parameter_bcc(el.atomic_radius)

        # Create BCC structure using space group Im-3m (229)
        structure = Structure.from_spacegroup("Im-3m", Lattice.cubic(a), [el.name], [[0, 0, 0]])

        # Example usage
        scaling_factors = calculate_bcc_scaling_factors(total_atoms)
        print(f"Scaling factors for BCC structure to achieve ~{total_atoms} atoms: {scaling_factors}")
        supercell = structure.make_supercell(scaling_factors)


    # get a composition dictionary that lists the element and how many atoms it has in the formula
    comp_dict = composition.to_reduced_dict
    logging.debug(f'Composition dictionary: {comp_dict}')

    # Calculate the total number of atoms for a composition that will be in supercell size of total_atoms
    num_atoms = {el: int(round(total_atoms * amt)) for el, amt in comp_dict.items()}

    # Ensure total atoms match exactly 100, adjust the largest if necessary
    # find largest number in comp_dict
    el_with_most_atoms = max(num_atoms, key=num_atoms.get)
    actual_total_atoms = sum(num_atoms.values())
    if actual_total_atoms < total_atoms:
        num_atoms[el_with_most_atoms] += total_atoms - actual_total_atoms  # Adjust 

    # Randomly replace atoms to achieve the desired composition
    # Flatten the list of atoms based on num_atoms
    desired_atoms = [el for el, num in num_atoms.items() for _ in range(num)]
    # Randomly shuffle the atoms
    np.random.shuffle(desired_atoms)

    # Replace atoms in the supercell with the shuffled atoms
    for i, specie in enumerate(desired_atoms):
        supercell.replace(i, specie)

    # If the supercell has more atoms than needed, remove the excess
    if len(supercell) > total_atoms:
        del supercell.sites[total_atoms:]


    return supercell


def create_disordered_structure(composition: Composition, crystal: str, total_atoms=100 ):
    valid_crystal_types = {"fcc", "bcc"}
    crystal = crystal.lower()
    assert crystal in valid_crystal_types, f"{crystal} is not a valid crystal type. Valid crystal types are {', '.join(valid_crystal_types)}."

    # Assuming get_most_common_element returns an Element object
    el = get_most_common_element(composition)

    # Assuming composition is a pymatgen Composition object
    comp_dict = composition.get_el_amt_dict()

    if crystal == "fcc":
        a = estimate_lattice_parameter_fcc(el.atomic_radius)
        scaling_factors = calculate_fcc_scaling_factors(total_atoms)
        print(f"Scaling factors for FCC structure to achieve ~{total_atoms} atoms: {scaling_factors}")
    elif crystal == "bcc":
        a = estimate_lattice_parameter_bcc(el.atomic_radius)
        scaling_factors = calculate_bcc_scaling_factors(total_atoms)
        print(f"Scaling factors for BCC structure to achieve ~{total_atoms} atoms: {scaling_factors}")

    # Create a structure with disordered composition directly
    species = [{Species(el, 1): amt for el, amt in comp_dict.items()}]
    coords = [[0, 0, 0]]  # Assuming a single site for simplicity; adjust as needed for your structure

    # Create the initial structure
    structure = Structure.from_spacegroup("Fm-3m" if crystal == "fcc" else "Im-3m", Lattice.cubic(a), species, coords)
    supercell = structure * np.array(scaling_factors)

    return supercell


