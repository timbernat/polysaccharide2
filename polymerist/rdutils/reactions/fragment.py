'''For fragmenting molecules by reaction and residue information'''

__author__ = 'Timotej Bernat'
__email__ = 'timotej.bernat@colorado.edu'

from typing import Generator
from abc import ABC, abstractmethod
from itertools import combinations

from rdkit import Chem
from rdkit.Chem import rdqueries, Mol

from .reactions import RxnProductInfo
from ..labeling.bondwise import get_shortest_path_bonds


# HELPER FUNCTIONS
HEAVY_FORMER_LINKER_QUERY_ATOM : Chem.QueryAtom = rdqueries.HasPropQueryAtom('was_dummy') # query for atoms with the property "was_dummy" set
HEAVY_FORMER_LINKER_QUERY_ATOM.ExpandQuery(rdqueries.AAtomQueryAtom()) # expand query to only match heavy atoms

def bridgehead_atom_ids(product : Chem.Mol) -> Generator[int, None, None]:
    '''
    Generates the indices of all atoms in a reaction product which were tagged
    as R-group bridgehead (i.e. wild) atoms in the reaction template definition
    '''
    for bh_atom in product.GetAtomsMatchingQuery(HEAVY_FORMER_LINKER_QUERY_ATOM):
        yield bh_atom.GetIdx()
        
# ABSTRACT BASE FOR FRAGMENTATION STRATEGIES
class IntermonomerBondIdentificationStrategy(ABC):
    '''Abstract base for Intermonomer Bond Identification Strategies for fragmentation during in-silico polymerization'''
    @abstractmethod
    def _locate_intermonomer_bonds(self, product : Mol, product_info : RxnProductInfo) -> Generator[int, None, None]:
        '''
        Generates the indices of all identified inter-monomer bonds by molecule
        MUST BE IMPLEMENTED in order to define behavior of fragmentation strategy
        '''
        pass

    def locate_intermonomer_bonds(self, product : Mol, product_info : RxnProductInfo) -> Generator[int, None, None]:
        '''Generates the indices of all identified inter-monomer bonds by molecule, no more than once each'''
        bonds_already_cut : set[int] = set()
        for bond_id in self._locate_intermonomer_bonds(product, product_info=product_info):
            if bond_id not in bonds_already_cut: # bond cleavage must be idempotent, to avoid attempting to cut bonds which no longer exist
                yield bond_id
                bonds_already_cut.add(bond_id)   # mark bond as visited to avoid duplicate cuts

    def produce_fragments(self, product : Mol, product_info : RxnProductInfo, separate : bool=True):
        '''Apply break all bonds identified by this IBIS algorithm and return the resulting fragments'''
        fragments = Chem.FragmentOnBonds(
            mol=product,
            bondIndices=self.locate_intermonomer_bonds(product, product_info) # TODO : check that the multiplicity of any bond to cut is no greater than the bond order
        ) # TODO : add config for "dummyLabels" arg to support port flavor setting
        if separate:
            return Chem.GetMolFrags(fragments, asMols=True, sanitizeFrags=False) # avoid disruptive sanitization (can be done in post)
        return fragments # if separation is not requested, return as single unfragmented molecule object
IBIS = IntermonomerBondIdentificationStrategy # shorthand alias for convenience

## CONCRETE IMPLEMENTATIONS
class ReseparateRGroups(IBIS):
    '''IBIS which cleaves any new bonds formed between atoms that were formerly the start of an R-group in the reaction template'''
    def _locate_intermonomer_bonds(self, product: Mol, product_info : RxnProductInfo) -> Generator[int, None, None]:
        for bridgehead_id_pair in combinations(bridgehead_atom_ids(product), 2):                    # for every pair of R-group bridgehead atoms...
            for new_bond_id in product_info.new_bond_ids_to_map_nums.keys():                        # find the path(s) with fewest bonds between the bridgeheads... 
                if new_bond_id in get_shortest_path_bonds(product, *bridgehead_id_pair):   # and select for cutting any newly-formed bonds found along that path
                    yield new_bond_id
                                                    