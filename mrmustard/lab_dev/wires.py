# Copyright 2023 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Classes for supporting tensor network functionalities."""

from __future__ import annotations
from typing import Iterable, Optional
import numpy as np
from mrmustard import settings


class Wires:
    r"""A class with wire functionality for tensor network applications.
    Anything that wants wires should use an object of this class.
    For the time being, wires are tuples of type (int, Optional[int]), where
    the first int is the id of the wire of self, and the second int is the id
    of the wire the first is attached to, if any. The second int is None if
    the wire is not attached to anything.
    The Wires class is an orchestrator of the individual wires.

    Wires are arranged into four sets (each of the four sets can span multiple modes):

    input bra --->|   |---> output bra
    input ket --->|   |---> output ket
    
    A Wires object can return a new Wires object with a subset of the modes.
    Available subsets are:
    - input/output
    - bra/ket
    - modes (sorted by default)

    E.g. ``wires.input`` returns a Wires object with only the input wires
    (on bra/ket side and all modes). Or ``wires.bra[(1,2)] returns a Wires
    object with only the bra wires on modes 1 and 2 (on input/output side).

    Wires objects provide set

    Args:
        modes_out_bra (list[int]): The output modes on the bra side.
        modes_in_bra (list[int]): The input modes on the bra side.
        modes_out_ket (list[int]): The output modes on the ket side.
        modes_in_ket (list[int]): The input modes on the ket side.
    """

    def __init__(
        self,
        modes_out_bra: Iterable[int] = [],
        modes_in_bra: Iterable[int] = [],
        modes_out_ket: Iterable[int] = [],
        modes_in_ket: Iterable[int] = [],
    ) -> None:
        if any(m != sorted(m) for m in [modes_out_bra, modes_in_bra, modes_out_ket, modes_in_ket]):
            raise ValueError("modes must be sorted")
        self._modes = sorted(
            set(modes_out_bra) | set(modes_in_bra) | set(modes_out_ket) | set(modes_in_ket)
        )
        randint = settings.rng.integers  # MM random number generator
        out_bra = {m: randint(1, 2**62) if m in modes_out_bra else 0 for m in self._modes}
        in_bra = {m: randint(1, 2**62) if m in modes_in_bra else 0 for m in self._modes}
        out_ket = {m: randint(1, 2**62) if m in modes_out_ket else 0 for m in self._modes}
        in_ket = {m: randint(1, 2**62) if m in modes_in_ket else 0 for m in self._modes}

        self._ids = np.array(
            [[out_bra[m], in_bra[m], out_ket[m], in_ket[m]] for m in self._modes], dtype=np.int64
        )
        self.mask = np.ones_like(self._ids)  # multiplicative mask

    @property
    def ids(self) -> np.ndarray:
        "The ids of the wires in the standard order (bra/ket x out/in x mode)."
        return self._ids * self.mask
    
    # def __len__(self):
    #     return np.sum(self.ids[self.ids > 0])
    
    # @ids.setter
    # def ids(self, value: int | Wires):
    #     if isinstance(value, int):
    #         assert value >= 0, "wire ids must be non-negative"
    #         assert np.sum(self.ids > 0) == 1, "there must be a single wire to set"
    #         self._ids[self.ids > 0] = value
    #     elif isinstance(value, Wires):
    #         assert np.all(value.ids[value.ids > 0] == self.ids[self.ids > 0]), "wires mismatch"
    #         self._ids[self.ids > 0] = value.ids[value.ids > 0]
    #     else:
    #         raise ValueError("Expected int or Wires object.")

    @property
    def modes(self) -> list[int]:
        "The set of modes of the available wires."
        return [m for m in self._modes if any(self.ids[self._modes.index(m)] > 0)]
    
    @property
    def is_ambiguous(self) -> bool:
        "Whether the input/output wires are different."
        return self.output.modes != self.input.modes

    def new(self, ids: Optional[np.ndarray] = None) -> Wires:
        "A copy of self with the given ids or new ids if ids is None."
        if ids is None:
            w = Wires(
                self.bra.output.modes,
                self.bra.input.modes,
                self.ket.output.modes,
                self.ket.input.modes,
            )
        else:
            w = Wires()
            w._modes = self._modes
            w._ids = ids
        w.mask = self.mask.copy()
        return w

    @property
    def indices(self) -> list[int]:
        r"""Returns the array of indices of the given id in the standard order.
        (bra/ket x out/in x mode). Use this to get the indices for bargmann contractions.
        """
        flat = self.ids.T.ravel()
        flat = flat[flat != 0]
        return np.where(flat > 0)[0].tolist()

    def masked_view(self, masked_rows: list[int] = [], masked_cols: list[int] = []) -> Wires:
        r"""A view of this Wires object with the given mask."""
        w = self.new(self._ids)
        w.mask[masked_rows, :] = -1
        w.mask[:, masked_cols] = -1
        return w

    @property
    def input(self) -> Wires:
        "A view of this Wires object without output wires"
        return self.masked_view(masked_cols=[0, 2])

    @property
    def output(self) -> Wires:
        "A view of this Wires object without input wires"
        return self.masked_view(masked_cols=[1, 3])

    @property
    def ket(self) -> Wires:
        "A view of this Wires object without bra wires"
        return self.masked_view(masked_cols=[0, 1])

    @property
    def bra(self) -> Wires:
        "A view of this Wires object without ket wires"
        return self.masked_view(masked_cols=[2, 3])

    def __getitem__(self, modes: Iterable[int] | int) -> Wires:
        "A view of this Wires object with wires only on the given modes."
        modes = [modes] if isinstance(modes, int) else modes
        idxs = [list(self._modes).index(m) for m in set(self._modes).difference(modes)]
        return self.masked_view(masked_rows=idxs)


    @property
    def adjoint(self) -> Wires:
        "A new Wires object with ket <-> bra."
        w = self.new(self._ids[:, [1, 0, 3, 2]])
        w.mask = self.mask[:, [1, 0, 3, 2]]
        return w

    @property
    def dual(self) -> Wires:
        "A new Wires object with input <-> output."
        w = self.new(self._ids[:, [2, 3, 0, 1]])
        w.mask = self.mask[:, [2, 3, 0, 1]]
        return w



        