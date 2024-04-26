'''Core tools for manipulating integer lattices in N-dimensions'''

from typing import Iterable
from ...genutils.typetools.numpytypes import Shape, N, M
from ...genutils.typetools.categorical import ListLike

import numpy as np
from itertools import product as cartesian_product
from .coordinates import Coordinates


def generate_int_lattice(*dims : Iterable[int]) -> np.ndarray[Shape[M, N], int]:
    '''Generate all N-D coordinates of points on a integer lattice with the sizes of all D dimensions given'''
    return np.fromiter(
        iter=cartesian_product(*[
            range(d)
                for d in dims
        ]),
        dtype=np.dtype((int, len(dims)))
    )

# TODO : implement enumeration of integral points within an N-simplex

class CubicIntegerLattice(Coordinates):
    '''For representing an n-dimensional integer lattice, consisting of all n-tuples of integers with values constrained by side lengths in each dimension'''
    def __init__(self, sidelens : np.ndarray[Shape[N], int]) -> None: # TODO: implement more flexible input support (i.e. star-unpacking, listlikes, etc.)
        assert(sidelens.ndim == 1)
        super().__init__(generate_int_lattice(*self.sidelens))

    def sidelens_as_str(self, multip_char : str='x') -> str:
        '''Stringify the lattice sidelengths'''
        return multip_char.join(str(i) for i in self.sidelens)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.n_dims}-dimensional, {self.sidelens_as_str()})'

    # LATTICE DIMENSIONS
    @property
    def capacity(self) -> int: # referred to as "M" in typehints
        '''The maximum number of points that the lattice could contains'''
        return np.prod(self.sidelens)

    @property
    def lex_ordered_weights(self) -> np.ndarray[Shape[N], int]:
        '''Vector of the number of points corresponding
        Can be viewed as a linear transformation between indices and point coordinates when coords are placed in lexicographic order'''
        return np.concatenate(([1], np.cumprod(self.sidelens)[:-1]))

    # SUBLATTICE DECOMPOSITION
    @property
    def odd_even_idxs(self) -> tuple[np.ndarray[Shape[M], int], np.ndarray[Shape[M], int]]: # TOSELF: each subarray actually has length M/2 (+1 if capacity is odd), not sure how to typehint that though
        '''Return two vectors of indices, corresponding to points in the "odd" and "even" non-neighboring sublattices, respectively'''
        parity_vector = np.mod(self.points.sum(axis=1), 2) # remainder of sum of coordinates of each point; corresponds to the condition that a single step along any dimension should invert parity
        is_odd = parity_vector.astype(bool) # typecast as booleans to permit indexing (and make intent a bit clearer)

        return np.where(is_odd), np.where(~is_odd)

    @property
    def odd_idxs(self) -> np.ndarray[Shape[M], int]:
        '''Indices of the point in the in "odd" sublattice'''
        return self.odd_even_idxs[0]

    @property
    def even_idxs(self) -> np.ndarray[Shape[M], int]:
        '''Indices of the point in the in "even" sublattice'''
        return self.odd_even_idxs[1]

    @property
    def odd_sublattice(self) -> np.ndarray[Shape[M, N], int]:
        '''Returns points within the odd sublattice of the lattice points'''
        return self.points[self.odd_idxs]
    odd_points = odd_sublattice # alias for convenience

    @property
    def even_sublattice(self) -> np.ndarray[Shape[M, N], int]:
        '''Returns points within the even sublattice of the lattice points'''
        return self.points[self.even_idxs]
    even_points = even_sublattice # alias for convenience