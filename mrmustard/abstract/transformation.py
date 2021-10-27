# Copyright 2021 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np  # for repr
from abc import ABC, abstractproperty
from mrmustard.core import gaussian, fock
from mrmustard.abstract import State
from mrmustard._typing import *
import mrmustard.constants as const

class Transformation(ABC):
    r"""
    Base class for all transformations.
    Note that measurements are CP but not TP, so they have their own abstract class.
    Transformations include:
        * unitary transformations
        * non-unitary CPTP channels
    """

    def __call__(self, state: State) -> State:
        d = self.d_vector()
        X = self.X_matrix()
        Y = self.Y_matrix()
        cov, means = gaussian.CPTP(state.cov, state.means, X, Y, d, self.modes)
        return State.from_gaussian(cov, means, mixed=state.is_mixed or Y is not None)

    def __repr__(self):
        with np.printoptions(precision=6, suppress=True):
            lst = [f"{name}={np.array(np.atleast_1d(self.__dict__[name]))}" for name in self.param_names]
            return f"{self.__class__.__qualname__}(modes={self.modes}, {', '.join(lst)})"

    @property
    def modes(self) -> Sequence[int]:
        if self._modes in (None, []):
            if (d := self.d_vector()) is not None:
                self._modes = list(range(d.shape[-1] // 2))
            elif (X := self.X_matrix()) is not None:
                self._modes = list(range(X.shape[-1] // 2))
            elif (Y := self.Y_matrix()) is not None:
                self._modes = list(range(Y.shape[-1] // 2))
        return self._modes

    @property
    def bell(self):
        "N pairs of two-mode squeezed vacuum where N is the number of modes of the circuit"
        pass

    def X_matrix(self) -> Optional[Matrix]:
        return None

    def Y_matrix(self) -> Optional[Matrix]:
        return None

    def d_vector(self) -> Optional[Vector]:
        return None

    def fock(self, cutoffs=Sequence[int]):  # only single-mode for now
        unnormalized = self(self.bell).ket(cutoffs=cutoffs)
        return fock.normalize_choi_trick(unnormalized, const.TMSV_DEFAULT_R)

    def trainable_parameters(self) -> Dict[str, List[Trainable]]:
        return {"symplectic": [], "orthogonal": [], "euclidean": self._trainable_parameters}

    def __getitem__(self, items) -> Callable:
        r"""
        Allows transformations to be used as:
        output = op[0,1](input)  # e.g. acting on modes 0 and 1
        """
        if isinstance(items, int):
            modes = [items]
        elif isinstance(items, slice):
            modes = list(range(items.start, items.stop, items.step))
        elif isinstance(items, (Sequence, Iterable)):
            modes = list(items)
        else:
            raise ValueError(f"{items} is not a valid slice or list of modes.")
        self._modes = modes
        return self