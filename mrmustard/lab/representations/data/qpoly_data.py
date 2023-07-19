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

from __future__ import annotations

import numpy as np

from typing import Optional, TYPE_CHECKING, Union

from mrmustard.lab.representations.data.matvec_data import MatVecData
from mrmustard.math import Math
from mrmustard.typing import RealMatrix, Scalar, Vector

# if TYPE_CHECKING: # This is to avoid the circular import issu with GaussianData<>QPolyData
#     from mrmustard.lab.representations.data.gaussian_data import GaussianData


math = Math()


class QPolyData(MatVecData):
    r"""Quadratic polynomial data for certain Representation objects.

    Quadratic Gaussian data is made of: quadratic coefficients, linear coefficients, constant.
    Each of these has a batch dimension, and the batch dimension is the same for all of them.
    They are the parameters of a Gaussian expressed as `c * exp(-x^T A x + x^T b)`.

    Args:
        mat:    quadratic coefficient
        vec:    linear coefficients
        c:      constant
    """

    def __init__(self, A: RealMatrix, b: Vector, c: Scalar = 1.0) -> None:
        # Done here because of circular import with GaussianData<>QPolyData
        # from mrmustard.lab.representations.data.gaussian_data import GaussianData

        # if isinstance(A, GaussianData):
        #     A, b, c = self._from_GaussianData(covmat=A)

        if self.helper_check_is_real_symmetric(A):
            super().__init__(mat=A, vec=b, coeffs=c)
        else:
            raise ValueError("Matrix A is not real symmetric.")

    @property
    def A(self) -> RealMatrix:
        return self.mat

    @property
    def b(self) -> Vector:
        return self.vec

    @property
    def c(self) -> Scalar:
        return self.coeffs

    def __mul__(self, other: Union[Scalar, QPolyData]) -> QPolyData:
        if isinstance(other, QPolyData):  # TODO: proof it against other objects
            new_a = self.A + other.A
            new_b = self.b + other.b
            new_coeffs = self.c * other.c
            return self.__class__(A=new_a, b=new_b, c=new_coeffs)
        else:
            try:  # scalar
                new_coeffs = self.c * other
                return self.__class__(self.A, self.b, new_coeffs)
            except TypeError as e:  # Neither same object type nor a scalar case
                raise TypeError(f"Cannot multiply {self.__class__} and {other.__class__}.") from e

    # @staticmethod
    # def _from_GaussianData(covmat:GaussianData
    #                        ) -> Tuple[Batch[Matrix], Batch[Vector], Batch[Scalar]] :
    #     r""" Extracts necessary information from a GaussianData object to build a QPolyData one.

    #     Args:
    #         A : the GaussianData representation of a state

    #     Returns:
    #         The necessary matrix, vector and coefficients to build a QPolyData object
    #     """
    #     covmat = -math.inv(covmat.cov)
    #     b = math.inv(covmat.cov) @ covmat.mean
    #     pre_coeffs = np.einsum("bca,bcd,bde->bae", covmat.mean, math.inv(covmat.cov), covmat.mean)
    #     new_coeffs = covmat.coeff * pre_coeffs

    #     return (covmat, b, new_coeffs)
