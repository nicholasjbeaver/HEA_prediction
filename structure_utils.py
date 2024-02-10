from pymatgen.core.structure import Structure
from pymatgen.core.lattice import Lattice
from pymatgen.core.composition import Composition
from pymatgen.core.periodic_table import Element

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

def adjust_equiatomic_composition(comp: Composition):
    """
    If any of the elements are fractional, adjust all of the others that aren't specified to the equivelent fraction as if
    they were equiatomic. 
    e.g., Al0.875CoCrFeNi would be considered as Al being 87.5 and the rest equiatomic
    e.g., Al2CoCrFeNi would be considered as Al being 1 and the rest would be 1, so it would be stoichiometric
    """
    #TODO: verify that everything adds up to 1'ish
    #TODO: verify that any partial fractional compositions do not add up to be more than 1

    # Initialize a dictionary to hold the element proportions
    element_proportions = {}
    
    # Check if the composition is already stoichiometric
    if is_stoichiometric(comp):
        # If stoichiometric, return the original composition
        return comp
    
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

def get_max_radius_for_material(comp: Composition):
    max_radius = 0
    for element in comp.elements:
        if element.atomic_radius > max_radius:
            max_radius = element.atomic_radius

    logging.info(f"Maxiumum Atomic radius for {comp} is {max_radius}")

    return max_radius



def create_supercell_structure(composition: Composition, total_atoms=100 ):

    # Calculate the number of each atom
    num_atoms = {el: int(round(total_atoms * amt)) for el, amt in composition.items()}

    # Ensure total atoms match exactly 100, adjust the largest if necessary
    actual_total_atoms = sum(num_atoms.values())
    if actual_total_atoms < total_atoms:
        num_atoms['Al'] += total_atoms - actual_total_atoms  # Adjust 

    # Step 2: Create an initial FCC structure for Al (chosen arbitrarily)
    a = get_weighted_average_radius_for_material(composition)
    lattice = Lattice.cubic(a)
    structure = Structure(lattice, ['Al'], [[0, 0, 0]])  # FCC position

    # Step 3: Generate an approximate supercell
    # For FCC, each cell contains 4 atoms. Find the smallest cube number >= total_atoms/4 and take its cubic root for scaling
    scale_factor = round((total_atoms / 4) ** (1/3))
    if scale_factor ** 3 * 4 < total_atoms:
        scale_factor += 1  # Ensure we have at least total_atoms
    supercell = structure.copy()
    supercell.make_supercell([scale_factor, scale_factor, scale_factor])

    # Step 4: Randomly replace atoms to achieve the desired composition
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

    print(supercell)
