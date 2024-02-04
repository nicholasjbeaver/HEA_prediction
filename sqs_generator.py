from pymatgen.core import Lattice, Structure
from pymatgen.command_line import mcsqs_caller
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

    '''
    sqs_list = cint_sqs(primitive_structure)

    logging.info(  sqs_list)
    '''

