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

from __future__ import annotations

__all__ = ["Circuit"]

from mrmustard.utils.types import *
from mrmustard import settings
from mrmustard.utils.xptensor import XPMatrix, XPVector
from mrmustard.lab.abstract import Transformation
from mrmustard.lab.states import TMSV
from mrmustard.lab.abstract import State


class Circuit(Transformation):
    def __init__(self, ops: Sequence = []):
        self._ops: List = [o for o in ops]
        self.reset()

    def reset(self):
        self._compiled: bool = False
        self._modes: List[int] = []

    @property
    def num_modes(self) -> int:  # TODO: improve this
        all_modes = set()
        for op in self._ops:
            all_modes = all_modes | set(op.modes)
        return len(all_modes)

    def __call__(self, state: State) -> State:
        for op in self._ops:
            state = op(state)
        return state

    @property
    def XYd(self) -> Tuple[Matrix, Matrix, Vector]:  # NOTE: Overriding Transformation.XYd for efficiency
        X = XPMatrix(like_1=True)
        Y = XPMatrix(like_0=True)
        d = XPVector()
        for op in self._ops:
            opX = XPMatrix.from_xxpp(op.X_matrix, modes=(op.modes, op.modes), like_1=True)
            opY = XPMatrix.from_xxpp(op.Y_matrix, modes=(op.modes, op.modes), like_0=True)
            opd = XPVector.from_xxpp(op.d_vector, modes=op.modes)
            if opX.shape is not None and opX.shape[-1] == 1 and len(op.modes) > 1:
                opX = opX.clone(len(op.modes), modes=(op.modes, op.modes))
                opY = opY.clone(len(op.modes), modes=(op.modes, op.modes))
                opd = opd.clone(len(op.modes), modes=op.modes)
            X = opX @ X
            Y = opX @ Y @ opX.T + opY
            d = opX @ d + opd
        return X.to_xxpp(), Y.to_xxpp(), d.to_xxpp()

    @property
    def is_gaussian(self):
        return all(op.is_gaussian for op in self._ops)

    def extend(self, obj):
        result = self._ops.extend(obj)
        self.reset()

    def append(self, obj):
        result = self._ops.append(obj)
        self.reset()

    def __len__(self):
        return len(self._ops)

    def __repr__(self) -> str:
        return f"Circuit | {len(self._ops)} ops | compiled = {self._compiled}"

    @property
    def trainable_parameters(self) -> Dict[str, List[Trainable]]:
        r"""
        Returns the dictionary of trainable parameters
        """
        symp = [
            p for op in self._ops for p in op.trainable_parameters["symplectic"] if hasattr(op, "trainable_parameters")
        ]
        orth = [
            p for op in self._ops for p in op.trainable_parameters["orthogonal"] if hasattr(op, "trainable_parameters")
        ]
        eucl = [
            p for op in self._ops for p in op.trainable_parameters["euclidean"] if hasattr(op, "trainable_parameters")
        ]
        return {"symplectic": symp, "orthogonal": orth, "euclidean": eucl}