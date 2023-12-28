from POSCAR_generator import generate_poscar_files, write_vasp
from energy_calculation import calculate_energy
from dataclasses import dataclass
from typing import List


@dataclass
class input_message:    
    alloy: str
    crystal: str

@dataclass
class output_message:
    alloy: str
    crystal: str
    energy: float
    poscar_file: List[str]

def process_message(message):

    alloy = message.alloy
    crystal = message.crystal    
    poscar = generate_poscar_files(alloy, crystal)
    vasp_file = write_vasp(poscar, f'vasp_files_temp/{alloy}_{crystal}.vasp')
    energy = calculate_energy(vasp_file)

    return output_message(alloy, crystal, energy, poscar)

if __name__ == "__main__":
    test_dict ={'AlFe': 'FCC', 'AlFe3': 'BCC', 'Al2Fe': 'FCC'}
    
    for alloy, crystal in test_dict.items():
        alloy = alloy
        crystal = crystal
        message = input_message(alloy, crystal)
        output = process_message(message)
        print(output)