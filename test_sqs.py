# import all function from sqs_generator
import sqs_generator as sqs
import structure_utils as su
from pymatgen.core.composition import Composition
from pymatgen.command_line import mcsqs_caller


# set the default logging level to INFO
import logging
logging.basicConfig(level=logging.DEBUG)


if __name__ == '__main__':

    materials_list = ["Al0.875CoCrFeNi", "Al0.875CoCrFeNi0.10", "CoCrFeNi", "Al4CoCrFeNi", "VCoNi"]

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
        structure = su.create_random_supercell_structure(adjusted_composition, "fcc", total_atoms=60)
        print(f"{structure}")

    #--------  Test pmg_sqs -------------------

    # get first material in materials_list
    material = materials_list[0]

    comp = Composition(material)
    adjusted_composition = su.adjust_equiatomic_composition(comp)
    #structure = su.create_random_supercell_structure(adjusted_composition, "fcc", total_atoms=60)
    structure = su.create_disordered_structure(adjusted_composition, "fcc", total_atoms=60)
    cutoffs = su.propose_fcc_cutoffs(structure)

    logging.info(f"Generating SQS using {structure}\n with clusters: {cutoffs}")
    mcsqs_caller.run_mcsqs(structure = structure, clusters = cutoffs)
