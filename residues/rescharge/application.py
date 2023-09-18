'''Utilities for generating, storing, and applying partial charges to OpenFF Molecules'''

import logging
LOGGER = logging.getLogger(__name__)

from typing import Any, Iterable, Optional
from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
import numpy as np

from openff.toolkit.topology.molecule import Molecule
from openmm.unit import elementary_charge

from .chgtypes import ChargesByResidue
from ...genutils.decorators.classmod import register_subclasses
from ...genutils.decorators.functional import optional_in_place


# FUNCTIONS FOR MAPPING CHARGES ONTO MOLECULES
@optional_in_place
def apply_averaged_res_chgs(mol : Molecule, chgs_by_res : ChargesByResidue) -> None:
    '''Takes an OpenFF Molecule and a residue-wise map of averaged partial charges and applies the mapped charges to the Molecule'''
    new_charges = [
        chgs_by_res.charges[atom.metadata['residue_name']][atom.metadata['substructure_id']]
            for atom in mol.atoms
    ]
    new_charges = np.array(new_charges) * elementary_charge # convert to unit-ful array (otherwise assignment won't work)
    mol.partial_charges = new_charges
    

# ABSTRACT AND CONCRETE CLASSES FOR CHARGING MOLECULES
@register_subclasses(key_attr='METHOD_NAME')
class MolCharger(ABC):
    '''Base interface for defining various methods of generating and storing atomic partial charges'''
    @abstractproperty
    @classmethod
    def METHOD_NAME(cls):
        '''For setting the name of the method as a class attribute in child classes'''
        pass

    @abstractmethod
    def _charge_molecule(self, uncharged_mol : Molecule) -> Molecule:
        '''Method for assigning molecular partial charges - concrete implementation in child classes'''
        pass

    def charge_molecule(self, uncharged_mol : Molecule) -> Molecule:
        '''Wraps charge method call with logging'''
        LOGGER.info(f'Assigning partial charges via the "{self.METHOD_NAME}" method')
        cmol = self._charge_molecule(uncharged_mol)
        LOGGER.info(f'Successfully assigned "{self.METHOD_NAME}" charges')

        return cmol

class ABE10Charger(MolCharger):
    '''Charger class for AM1-BCC-ELF10 exact charging'''
    METHOD_NAME = 'ABE10_exact'

    def _charge_molecule(self, uncharged_mol : Molecule) -> Molecule:
        '''Concrete implementation for AM1-BCC-ELF10'''
        return Molecule.assign_partial_charges(uncharged_mol, toolkit='OpenEye Toolkit', partial_charge_method='am1bccelf10', force_match=True)

class EspalomaCharger(MolCharger):
    '''Charger class for AM1-BCC-ELF10 exact charging'''
    METHOD_NAME = 'Espaloma_AM1BCC'

    def _charge_molecule(self, uncharged_mol : Molecule) -> Molecule:
        return Molecule.assign_partial_charges(uncharged_mol, toolkit='Espaloma Charge Toolkit', partial_charge_method='espaloma-am1bcc', force_match=True)