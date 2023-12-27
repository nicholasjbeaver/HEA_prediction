from POSCAR_generator import generate_poscar_files
from dataclasses import dataclass

@dataclass
class input_message:    
    alloy: str
    crystal: str

@dataclass
class output_message:
    alloy: str
    crystal: str
    poscar_file: str

def process_message(message):
    alloy = message.alloy
    crystal = message.crystal
    poscar = generate_poscar_files(alloy, crystal)
    return output_message(alloy, crystal, poscar)

if __name__ == "__main__":
    alloy = 'AlFe'
    crystal = 'FCC'
    message = input_message(alloy, crystal)
    output = process_message(message)
    print(f"Alloy: {output.alloy}")
    print(f"Crystal: {output.crystal}")
    print(f"POSCAR file: {output.poscar_file}")