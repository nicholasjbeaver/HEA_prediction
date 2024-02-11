# import all function from sqs_generator
import sqs_generator as sqs
import structure_utils as su
from pymatgen.core.composition import Composition

# set the default logging level to INFO
import logging
logging.basicConfig(level=logging.DEBUG)


if __name__ == '__main__':

    materials_list = ["Al0.875CoCrFeNi", "Al0.875CoCrFeNi0.10", "CoCrFeNi", "Al4CoCrFeNi"]

    #--------  Test composition -------------------
    
    for material in materials_list:
        comp = Composition(material)
        adjusted_composition = su.adjust_equiatomic_composition(comp)
        print(adjusted_composition)


    #--------  Test average atomic size -------------------

    for material in materials_list:
        comp = Composition(material)
        adjusted_composition = su.adjust_equiatomic_composition(comp)
        print(f"Average atomic size: {su.get_weighted_average_radius_for_material(adjusted_composition)} Angstroms")
        print(f'Maximum atomic size: {su.get_largest_element(adjusted_composition)} Angstroms')


    #--------  Test create_random_supercell_structure -------------------
    for material in materials_list:
        comp = Composition(material)
        adjusted_composition = su.adjust_equiatomic_composition(comp)
        structure = su.create_random_supercell_structure(adjusted_composition, "fcc", total_atoms=100)
        print(f"{structure}")

    #--------  Test pmg_sqs -------------------
  
    # create a disordered V-Co-Ni FCC structure
    comp = su.adjust_equiatomic_composition(Composition("VCoNi"))

    logging.info(f"Creating a disordered FCC structure for {comp}")

    #structure = create_random_supercell_structure(comp, total_atoms=100)

    #logging.info(f"Generating SQS using {structure}")
    #pmg_sqs(structure)