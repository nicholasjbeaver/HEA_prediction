import re
import random
import numpy as np
import os
import math

def find_mole_fractions(input_string):
    """
    Split the input string containing element codes and mole fractions into a dictionary.

    Args:
        input_string (str): The input string containing element codes and numbers.

    Returns:
        dict: A dictionary with element codes as keys and corresponding fractions as values.
    """
    pattern = r'([A-Z][a-z]?)(\d+(\.\d+)?)?'

    matches = re.findall(pattern, input_string)

    result_dict = {}

    for match in matches:
        code = match[0]
        if match[1]:
            result_dict[code] = float(match[1])
        else:
            result_dict[code] = 1.0

    mol_fractions = {}
    total_value = sum(result_dict.values())
    for key, value in result_dict.items():
        mol_fractions[key] = value / total_value

    return mol_fractions

def make_vasp(alloy, element_mol_fraction, filepath, output_file):
    """
    Generate a POSCAR file for a given alloy.

    inputs: alloy (str), element_mol_fraction (dict), filepath (str), output_file (str)

    returns: none (writes to file)
    """

    total_atoms = 32

    element_atom_count = {element: max(1, math.floor(total_atoms * fraction)) for element, fraction in element_mol_fraction.items()}

    # Calculate the current total and determine how many atoms are missing
    current_total = sum(element_atom_count.values())
    atoms_to_add = total_atoms - current_total

    # Distribute the remaining atoms
    for element in sorted(element_mol_fraction, key=lambda e: element_mol_fraction[e], reverse=True):
        if atoms_to_add <= 0:
            break
        element_atom_count[element] += 1
        atoms_to_add -= 1

    # Verify that the total now matches the desired number of atoms
    assert sum(element_atom_count.values()) == total_atoms, "Total atom count does not match."

    # Read the original file
    with open(filepath, 'r') as file:
        lines = file.readlines()

    # Insert the elements list into line 6
    lines[5] = ' '.join(element_mol_fraction.keys()) + '\n'

    # Insert the num_atoms list into line 7
    num_atoms_line = ' '.join(str(element_atom_count[element]) for element in element_mol_fraction.keys()) + '\n'
    lines[6] = num_atoms_line

    # Write the modified content to a new file
    with open(output_file, 'w') as file:
        file.writelines(lines)

    print(f"File modified and saved as {output_file}")

def generate_poscar_files(alloy):
    """
    Generate POSCAR files for a given alloy.

    inputs: alloy (str)

    returns: none (writes to file)
    """
    mol_fractions = find_mole_fractions(alloy)
    polymorphs = {'FCC':'FCC_32atom_template.txt', 'BCC':'BCC_32atom_template.txt'}

    for crystal, filepath in polymorphs.items():
        make_vasp(alloy, mol_fractions, filepath, f'vasp_files_temp/{alloy}_{crystal}.vasp')


if __name__ == '__main__':
    alloys = ['AlFe0.2CrCuCo', 'Al0.1Fe0.3Cr0.1Ti', 'AlFeTiVZrCuNiC']
    for alloy in alloys:
        generate_poscar_files(alloy)