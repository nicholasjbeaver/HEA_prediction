# import all function from sqs_generator
import sqs_generator as sqs
import structure_utils as su
from pymatgen.core.composition import Composition

# set the default logging level to INFO
import logging
logging.basicConfig(level=logging.DEBUG)


if __name__ == '__main__':

    #--------  Test composition -------------------
    # Example usage
    comp = Composition("Al0.875CoCrFeNi")
    adjusted_composition = su.adjust_equiatomic_composition(comp)
    print(adjusted_composition)

    comp = Composition("Al0.875CoCrFeNi0.10")
    adjusted_composition = su.adjust_equiatomic_composition(comp)
    print(adjusted_composition)

    # For a formula where all elements are equiatomic and none specified
    comp = Composition("CoCrFeNi")
    adjusted_composition = su.adjust_equiatomic_composition(comp)
    print(adjusted_composition)

    # For a formula where all elements are equiatomic and none specified
    comp = Composition("Al4CoCrFeNi")
    adjusted_composition = su.adjust_equiatomic_composition(comp)
    print(adjusted_composition)

    #--------  Test average atomic size -------------------
    # Example usage
    comp = Composition("Al0.875CoCrFeNi")
    adjusted_composition = su.adjust_equiatomic_composition(comp)
    print(f"Average atomic size: {su.get_weighted_average_radius_for_material(adjusted_composition)} Angstroms")
    print(f'Maximum atomic size: {su.get_max_radius_for_material(adjusted_composition)} Angstroms')

    comp = Composition("Al4CoCrFeNi")
    adjusted_composition = su.adjust_equiatomic_composition(comp)
    print(f"Average atomic size: {su.get_weighted_average_radius_for_material(adjusted_composition)} Angstroms")
    print(f'Maximum atomic size: {su.get_max_radius_for_material(adjusted_composition)} Angstroms')


    #--------  Test pmg_sqs -------------------
  
    # create a disordered V-Co-Ni FCC structure
    comp = su.adjust_equiatomic_composition(Composition("VCoNi"))

    logging.info(f"Creating a disordered FCC structure for {comp}")

    #structure = create_random_supercell_structure(comp, total_atoms=100)

    #logging.info(f"Generating SQS using {structure}")
    #pmg_sqs(structure)