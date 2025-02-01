'''For obtaining info from and for labelling individual RDKit Bonds'''

__author__ = 'Timotej Bernat'
__email__ = 'timotej.bernat@colorado.edu'

from typing import Any, Callable, Concatenate, Iterable, Optional, ParamSpec, Union
Params = ParamSpec('Params')

from itertools import combinations
from rdkit.Chem.rdchem import Bond, BondType, Mol

from .molwise import atom_ids_by_map_nums
from ...genutils.decorators.functional import optional_in_place


# BOND ID QUERYING    
def get_bonded_pairs(rdmol : Mol, *atom_ids : Iterable[int]) -> dict[int, tuple[int, int]]:
    '''Get bond and (begin,end) atom indices of all bonds which exist between any pair of atoms in an indexed list'''
    bond_id_dict = {}
    atom_id_pairs = combinations(atom_ids, 2)
    for atom_id_pair in atom_id_pairs:
        bond = rdmol.GetBondBetweenAtoms(*atom_id_pair)
        if bond is not None:
            bond_id_dict[bond.GetIdx()] = atom_id_pair
    return bond_id_dict

def get_bonded_pairs_by_map_nums(rdmol : Mol, *atom_map_nums : Iterable[int]) -> dict[int, tuple[int, int]]:
    '''Obtain bonded pair dict by atom map numbers instead of IDs'''
    return get_bonded_pairs(rdmol, *atom_ids_by_map_nums(rdmol, *atom_map_nums))

def get_bond_by_map_num_pair(rdmol : Mol, map_num_pair : tuple[int, int], as_bond : bool=True) -> Optional[Union[int, Bond]]:
    '''
    Get the bond spanning a pair of atoms with given pair of atom map numbers
    Returns the RDkit.Bond object if as_bond=True, and the index of the bond if as_bond=False
    
    If no bond exists between the atoms, will return None regardless of the value of "as_bond"
    '''
    bond = rdmol.GetBondBetweenAtoms(*atom_ids_by_map_nums(rdmol, *map_num_pair))
    if (not as_bond) and (bond is not None):
        return bond.GetIdx()
    return bond # returns bond or, implicitly, NoneType f no bond is found

# BOND ID LABELING
@optional_in_place
def assign_bond_id_labels(rdmol : Mol, bond_id_remap : Optional[dict[int, int]]=None) -> None:
    '''Draws bond indices over their positions when displaying a Mol. 
    Can optionally provide a dict mapping bond indices to some other integers'''
    if bond_id_remap is None:
        bond_id_remap = {} # avoid mutable default

    for bond in rdmol.GetBonds():
        bond.SetIntProp('bondNote', bond_id_remap.get(bond.GetIdx(), bond.GetIdx())) # check if map value exists, if not default to index

@optional_in_place
def clear_bond_id_labels(rdmol : Mol) -> None:
    '''Removes bond indices over their positions when displaying a Mol'''
    for bond in rdmol.GetBonds():
        bond.ClearProp('bondNote')