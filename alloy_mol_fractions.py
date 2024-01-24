import re

'''
take in a string representing a high entropy alloy and return a list of the elements as a dictionary
that includes the mole fraction of each element

ex: "AlCoCrFeNi" -> {'Al': 0.2, 'Co': 0.2, 'Cr': 0.2, 'Fe': 0.2, 'Ni': 0.2}

formula: AxBCD ->
%B, %C, %D = 1/(1+1+1+x)
%A = x/(1+1+1+x)

formula: AxByCD ->
%C, %D = 1/(1+1+x+y)
%A = x/(1+1+x+y)
%B = y/(1+1+x+y)

so in general:

formula: AxByCzDw ->
%A = x/(x+y+z+w)
%B = y/(x+y+z+w)
%C = z/(x+y+z+w)
%D = w/(x+y+z+w)
... etc

*should work for any combination of elements, not just 4
such that for Element(i)X(i)
X(i) = X(i)/(sum(X))

KEY FUNCTIONALITY:
1. take in a string representing a high entropy alloy
2. return a dictionary of the elements and the number next to the input string
3. calculate the mole fraction of each element
4. return a dictionary of the elements and their mole fractions

'''

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


if __name__ == 'main':
  elements = ['CoFeNi', 'CoFeNiSi0.25', 'AlCoCrFeNi', 'FeCCr']

  for element in elements:
      print(find_mole_fractions(element))
