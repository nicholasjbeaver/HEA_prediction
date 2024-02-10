# import all function from sqs_generator
import sqs_generator as sqs
from pymatgen.core.composition import Composition

# set the default logging level to INFO
import logging
logging.basicConfig(level=logging.INFO)


if __name__ == '__main__':

    #--------  Test composition -------------------
    # Example usage
    comp = Composition("Al0.875CoCrFeNi")
    adjusted_composition = sqs.adjust_equiatomic_composition(comp)
    print(adjusted_composition)

    comp = Composition("Al0.875CoCrFeNi0.10")
    adjusted_composition = sqs.adjust_equiatomic_composition(comp)
    print(adjusted_composition)

    # For a formula where all elements are equiatomic and none specified
    comp = Composition("CoCrFeNi")
    adjusted_composition_equiatomic = sqs.adjust_equiatomic_composition(comp)
    print(adjusted_composition_equiatomic)

    # For a formula where all elements are equiatomic and none specified
    comp = Composition("Al4CoCrFeNi")
    adjusted_composition_equiatomic = sqs.adjust_equiatomic_composition(comp)
    print(adjusted_composition_equiatomic)


    #--------  Test pmg_sqs -------------------
  
    # create a disordered V-Co-Ni FCC structure
    comp = adjusted_composition(Composition("VCoNi"))
    logging.info(f"Creating a disordered FCC structure for {comp}")

    # create a disordered FCC structure
    structure = Structure.from_spacegroup(
        "Fm-3m",
        lattice=Lattice.cubic(3.58),
        species=[composition],
        coords=[[0, 0, 0]]    )

    logging.info("Getting primitive structure")

    primitive_structure = structure.get_primitive_structure()

    logging.info("Generating SQS")

    pmg_sqs(primitive_structure)