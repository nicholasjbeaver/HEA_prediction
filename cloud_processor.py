from POSCAR_generator import generate_poscar_files, write_vasp
from energy_calculation import calculate_energy
from dataclasses import dataclass
from typing import List
import logging

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
    return output

if __name__ == "__main__":
    
    alloy = 'AlFe'
    crystal = 'FCC'
    do_relaxation = True
    message = input_message(alloy, crystal, do_relaxation)
    output = process_message(message)
    print(output)