# import all function from sqs_generator
import sqs_generator as sqs

# set the default logging level to INFO
import logging
logging.basicConfig(level=logging.INFO)


if __name__ == '__main__':

    material_str = 'Al0.875CoCrFeNi'

    comp = sqs.create_composition(material_str)


    #comp = sqs.normalize_composition(material_str)

    # Example usage
    formula = "Al0.875CoCrFeNi"
    adjusted_composition = sqs.adjust_equiatomic_composition(formula)
    print(adjusted_composition)

    # For a formula where all elements are equiatomic and none specified
    formula_equiatomic = "CoCrFeNi"
    adjusted_composition_equiatomic = sqs.adjust_equiatomic_composition(formula_equiatomic)
    print(adjusted_composition_equiatomic)

        # For a formula where all elements are equiatomic and none specified
    formula_equiatomic = "Al4CoCrFeNi"
    adjusted_composition_equiatomic = sqs.adjust_equiatomic_composition(formula_equiatomic)
    print(adjusted_composition_equiatomic)
