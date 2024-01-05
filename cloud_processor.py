from dataclasses import dataclass, asdict
from typing import List
import logging

# import local modules
from gcp_utils.settings import (
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_COMPUTE_REGION,
    logger
)
from gcp_utils import bq
from gcp_utils.utils import tznow, duck_str


from POSCAR_generator import generate_poscar_files, write_vasp
from energy_calculation import calculate_energy

# input message

@dataclass
class input_message:    
    alloy: str
    crystal: str
    do_relaxation: bool

# output message

@dataclass
class output_message:
    alloy: str
    mol_fractions: dict
    crystal: str
    energy: float
    poscar_file: List[str]

def process_message(message):

    logging.info(f'dataclass input:{message}')
    alloy = message.alloy
    crystal = message.crystal 

    unrelaxed_poscar_data, mol_fractions = generate_poscar_files(alloy, crystal)
    unrelaxed_vasp_file = write_vasp(unrelaxed_poscar_data, f'vasp_files_temp/{alloy}_{crystal}.vasp')
    energy, relaxed_poscar_data = calculate_energy(unrelaxed_vasp_file, relaxation=message.do_relaxation)

    if message.do_relaxation:
        poscar_data = relaxed_poscar_data
    else:
        poscar_data = unrelaxed_poscar_data
    
    output = output_message(alloy, mol_fractions, crystal, energy, poscar_data)
    logging.info(f'dataclass output:{output}')

    # store results in BQ
    store_results(output)

    return output

def store_results(output):
    logging.info(f'storing results')

    # convert the output to a dictionary and then to a string which will be parsed for the BQ insert
    data_record = duck_str(asdict(output))

    # BQ project name
    project_name = GOOGLE_CLOUD_PROJECT

    # BQ dataset name
    dataset_name = "experiments"

    # BQ table name
    table_name = "single_energy_calculations"

    # Insert a row into the database
    logger.debug(f"Putting record {data_record} into BigQuery at {project_name}.{dataset_name}.{table_name}")

    # BQ insert...this matches the table layout.
    bq.insert(table=table_name, project=project_name, dataset=dataset_name, 
                created_at=tznow(), ingestdata = "", metadata=data_record)


if __name__ == "__main__":
    
    alloy = 'AlFe'
    crystal = 'FCC'
    do_relaxation = False
    message = input_message(alloy, crystal, do_relaxation)
    output = process_message(message)
    print(output)