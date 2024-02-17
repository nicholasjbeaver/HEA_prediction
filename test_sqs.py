import logging
import os


# import all function from sqs_generator
import sqs_generator as sqs
import structure_utils as su
from pymatgen.core.composition import Composition
from pymatgen.command_line import mcsqs_caller
from gcp_utils.utils import tznow, duck_str, timing


# set the default logging level to INFO
logging.basicConfig(level=logging.DEBUG)

@timing
def mcsqs_wrapper(**kwargs):
    return(mcsqs_caller.run_mcsqs(**kwargs))


# main function

if __name__ == '__main__':

    materials_list = ["Al0.875CoCrFeNi", "Al0.875CoCrFeNi0.10", "CoCrFeNi", "Al4CoCrFeNi", "VCoNi"]

    #--------  Test composition -------------------
    '''
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
        structure = su.create_random_supercell_structure(adjusted_composition, "fcc", total_atoms=32)
        print(f"{structure}")
    '''
    #--------  Test pmg_sqs -------------------

    logging.info("\n------------ Testing mcsqs_caller ------------------")
    material = "Fe0.25Cr0.25Co0.25Ni0.25"

    comp = Composition(material)
    adjusted_composition = su.adjust_equiatomic_composition(comp)
    logging.info(f"Adjusted composition: {adjusted_composition}")
    structure, scaling_factors = su.create_disordered_structure(adjusted_composition, "fcc", lattice_parameter=3.54, total_atoms=32)
    cutoffs = su.propose_fcc_cutoffs(structure)

    # hardcode to match online version
    cutoffs = {"2": 3.54, "3": 3.54, "4": 3.54}
    

    logging.info(f"Generating SQS using {structure}\n with clusters: {cutoffs}")

    # make a temp directory name called temp_yyyymmddhhssmm
    temp_dir = f"./temp_{tznow().strftime('%Y%m%d%H%M%S')}"
    # make the directory
    os.mkdir(temp_dir)

    # run mcsqs

    sqs = mcsqs_wrapper(structure=structure, clusters=cutoffs, scaling=scaling_factors, directory=temp_dir, instances=1, search_time=30)
    
    # print the sqs structure to a temp file in temp_dir
    with open(f"{temp_dir}/sqs.json", "w") as f:
        f.write(duck_str(sqs))