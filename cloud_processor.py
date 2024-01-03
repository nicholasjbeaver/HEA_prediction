from POSCAR_generator import generate_poscar_files, write_vasp
from energy_calculation import calculate_energy
from dataclasses import dataclass
from typing import List
import logging


@dataclass
class input_message:    
    alloy: str
    crystal: str

@dataclass
class output_message:
    alloy: str
    mol_fractions: dict
    crystal: str
    energy: float
    poscar_file: List[str]

def process_message(message):

    alloy = message.alloy
    crystal = message.crystal    
    poscar, mol_fractions = generate_poscar_files(alloy, crystal)
    vasp_file = write_vasp(poscar, f'vasp_files_temp/{alloy}_{crystal}.vasp')
    energy = calculate_energy(vasp_file)
    output = output_message(alloy, mol_fractions, crystal, energy, poscar)
    logging.info(f'dataclass output:{output}')
    return output

if __name__ == "__main__":
    test_dict ={'AlFe': 'FCC', 'AlFe3': 'BCC', 'Al2Fe': 'FCC'}
    
    for alloy, crystal in test_dict.items():
        alloy = alloy
        crystal = crystal
        message = input_message(alloy, crystal)
        output = process_message(message)
        print(output)