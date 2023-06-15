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

from mrmustard.math import Math
from mrmustard.lab.representations import Representation
from mrmustard.lab.representations.data import QpolyData
from mrmustard.typing import Batch, Matrix, RealVector, RealMatrix, Scalar, Tensor, Vector

math = Math()

class Bargmann(Representation):
    r""" Fock representation of a state.
    
    Args:
        A: quadratic coefficients
        b: linear coefficients
        c: constants
    """

    def __init__(self, A:Batch[Matrix], b:Batch[Vector], c:Batch[Scalar]) -> None:
        self.data = QpolyData(A=A, b=b, c=c)


    @property
    def purity(self) -> Scalar:
        raise NotImplementedError("Get this of this state from other representations!")
    

    @property    
    def norm(self) -> float:
        raise NotImplementedError("Get this of this state from other representations!")


    @property
    def von_neumann_entropy(self) -> float:
        raise NotImplementedError("Get this of this state from other representations!")
    

    @property
    def number_means(self) -> RealVector:
        raise NotImplementedError("Get this of this state from other representations!")
    

    @property
    def number_cov(self) -> RealMatrix:
        raise NotImplementedError("Get this of this state from other representations!")
    

    @property
    def number_variances(self) -> int:
        raise NotImplementedError("Get this of this state from other representations!")
    

    @property
    def number_stdev(self) -> int:
        raise NotImplementedError("Get this of this state from other representations!")


    @property
    def probability(self) -> Tensor:
        raise NotImplementedError("Get this of this state from other representations!")
