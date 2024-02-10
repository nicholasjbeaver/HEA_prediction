from pymatgen.core.structure import Structure
from pymatgen.core.lattice import Lattice
from pymatgen.core.composition import Composition
from pymatgen.command_line import mcsqs_caller
from pymatgen.transformations.advanced_transformations import SQSTransformation
from smol.capp.generate.special.sqs import StochasticSQSGenerator
import logging
    

def corr_sqs(primitive_structure):

    # create a correlation vector based SQS generator
    generator_corr = StochasticSQSGenerator.from_structure(
        structure=primitive_structure,
        cutoffs={2: 7, 3: 5},  # cluster cutoffs as passed to cluster subspaces
        supercell_size=36,   # the search will be over supercells of 36 atoms
        feature_type="correlation",
        match_weight=1.0,  # weight given to the maximum diameter of perfectly matched vectors (see original publication for details)
    )

    # generate SQS using correlation vector based score
    generator_corr.generate(
    mcmc_steps=100000,  # steps per temperature
    temperatures=None,  # use default, but any sequence of decreasing temperatures can be passed for further control of SA
    max_save_num= None, # the default in this case will be 1000 (1% of mcmc_steps), the actual value of SQSs will likely be much less than that
    progress=True       # show progress bar for each temperature
    )

    sqs_corr_list = generator_corr.get_best_sqs(
        num_structures=generator_corr.num_structures,
        remove_duplicates=True,
    )

    return sqs_corr_list, generator_corr

def cint_sqs(primitive_structure):

    
    logging.info("Creationg a Stochastic SQS generator")    

    # create a cluster interaction vector based SQS generator
    generator_cint = StochasticSQSGenerator.from_structure(
        structure=primitive_structure,
        cutoffs={2: 7, 3: 5},
        supercell_size=36,
        feature_type="cluster-interaction",
        match_weight=1.0,
    )

    logging.info("Generating a bunch of SQS")
    # generate SQS using cluster interaction vector based score
    generator_cint.generate(
        mcmc_steps=100000, # steps per temperature
        temperatures=None,  # use default, but any sequence of decreasing temperatures can be passed for further control of SA
        max_save_num= None, # the default in this case will be 1000 (1% of mcmc_steps), the actual value of SQSs will likely be much less than that
        progress=True       # show progress bar for each temperature
    )

    sqs_cint_list = generator_cint.get_best_sqs(
        num_structures=generator_cint.num_structures,
        remove_duplicates=True,
    )

    return sqs_cint_list, generator_cint

def pmg_sqs(struc):

    clust={2: 7, 3: 5}
    mcsqs_caller.run_mcsqs(structure = struc, clusters = clust)


def is_stoichiometric(comp):
    """Check if the composition is stoichiometric (integer proportions or equiatomic)."""
    for amt in comp.get_el_amt_dict().values():
        if amt != 1 and not amt.is_integer():
            return False
    return True

def adjust_equiatomic_composition(formula):
    # Initialize a dictionary to hold the element proportions
    element_proportions = {}
    
    # Use Composition to parse the formula
    comp = Composition(formula)

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




def create_composition(material_string: str):

    # given an alloy string, assign concentrations.  If there is no number after the element, assume that it is 1
    # e.g. "Al0.875CoCrFeNi"
    comp = Composition(material_string)

    logging.info(f"Creating a disordered {material_string} structure")

    # print each element and its ratio
    for element, ratio in comp.fractional_composition.items():
        logging.info(f"Fractional composition: {element}: {ratio}")

    # print the number of atoms of each element in the composition
    for element, num_atoms in comp.element_composition.items():
        logging.info(f"Element composition: {element}: {num_atoms}")

    # print the total number of atoms in the composition
    logging.info(f"Number of atoms: {comp.num_atoms}")

    # print the reduced formula
    logging.info(f"Reduced formula: {comp.reduced_formula}")

    # print the comp.formula
    logging.info(f"Formula: {comp.formula}")

    # print the comp.alphabetical_formula
    logging.info(f"Alphabetical formula: {comp.alphabetical_formula}")

    # print the comp.reduced_composition
    logging.info(f"Reduced composition: {comp.reduced_composition}")

    # print the comp.element_composition
    logging.info(f"Element composition: {comp.element_composition}")
    

if __name__ == '__main__':

    # set up logging to log time and module
    logging.basicConfig(format='%(process)d: %(asctime)s: %(levelname)s: %(funcName)s: %(message)s', level=logging.INFO)
    
    
    # create a disordered V-Co-Ni FCC structure
    composition = {"V": 1.0/3.0, "Co": 1.0/3.0, "Ni": 1.0/3.0}

    logging.info("Creating a disordered V-Co-Ni FCC structure")

    # create a disordered V-Co-Ni FCC structure
    structure = Structure.from_spacegroup(
        "Fm-3m",
        lattice=Lattice.cubic(3.58),
        species=[composition],
        coords=[[0, 0, 0]]    )

    logging.info("Getting primitive structure")


    primitive_structure = structure.get_primitive_structure()

    logging.info("Generating SQS")

    pmg_sqs(primitive_structure)
  

    
    a = 3.8
    lattice = Lattice.cubic(a)
    structure = Structure(lattice, [{'Pd': 0.5, 'Cu': 0.5},{'Pd': 0.5, 'Cu': 0.5}, {'Pd': 0.5, 'Cu': 0.5},{'Pd': 0.5, 'Cu': 0.5}],[[0,0,0], [0.5,0.5,0], [0.5,0,0.5],[0,0.5,0.5]])
    print(structure)

    logging.info('making sqs transformation')
    sqstrans = SQSTransformation([1,1,1])
    print(sqstrans)

    logging.info('applying transformation')
    sqstrans.apply_transformation(structure)