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
import pytest
import numpy as np
from copy import deepcopy

from mrmustard.lab.representations.data.symplectic_data import SymplecticData
from mrmustard.typing import Matrix, Scalar, Vector
from mrmustard.utils.misc_tools import general_factory
from tests.test_lab.test_representations.test_data.tools_for_tests import (
    helper_mat_vec_unchanged_computed_coeffs_are_correct)

import operator as op


#########   Instantiating class to test  #########
@pytest.fixture
def TYPE():
    return SymplecticData

@pytest.fixture
def SYMPLECTIC() -> Matrix: #example taken from https://mathworld.wolfram.com/SymplecticGroup.html
    symp_mat = np.array([[1, 0, 0, 1], 
                         [0, 1, 1, 0],
                         [0, 0, 1, 0],
                         [0, 0, 0, 1],])
    return symp_mat

@pytest.fixture
def DISPLACEMENT() -> Vector:
    return np.ones(10) * 42

@pytest.fixture
def COEFFS() -> Scalar:
    return 42

@pytest.fixture
def PARAMS(SYMPLECTIC, DISPLACEMENT, COEFFS) -> dict:
    r"""Parameters for the class instance which is created."""
    params_dict = {'symplectic': SYMPLECTIC, 'displacement': DISPLACEMENT, 'coeffs':COEFFS}
    return params_dict


@pytest.fixture()
def DATA(TYPE, PARAMS) -> SymplecticData:
    r"""Instance of the class that must be tested."""
    return general_factory(TYPE, **PARAMS)


@pytest.fixture()
def OTHER(DATA) -> SymplecticData:
    r"""Another instance of the class that must be tested."""
    return deepcopy(DATA)
class TestSymplecticData():
    
    ####################  Init  ######################

    def test_init_without_coeffs_has_coeffs_equal_to_1(self, SYMPLECTIC, DISPLACEMENT):
        symplectic_data = SymplecticData(symplectic=SYMPLECTIC, displacement=DISPLACEMENT)
        assert symplectic_data.coeffs == 1

    def test_init_with_a_non_symplectic_matrix_raises_ValueError(self, DISPLACEMENT, COEFFS):
        non_symplectic_mat = np.eye(10) #TODO factory method for this
        non_symplectic_mat[0] += np.array(range(10))
        with pytest.raises(ValueError):
            SymplecticData(non_symplectic_mat, DISPLACEMENT, COEFFS)

    ##################  Negative  ####################
    # NOTE : tested in parent class

    ##################  Equality  ####################
    # NOTE : tested in parent class

    ##################  Addition  ####################
    # NOTE : tested in parent class

    ################  Subtraction  ###################
    # NOTE : tested in parent class

    #############  Scalar division  ##################
    # NOTE : tested in parent class

    ###############  Multiplication  #################
    
    def test_mul_raises_TypeError_with_object(self, DATA, OTHER):
        with pytest.raises(TypeError):
            OTHER * DATA

    @pytest.mark.parametrize('x', [0, 2, 10, 250])
    def test_mul_with_scalar_multiplies_coeffs_and_leaves_mat_and_vec_unaltered(self, DATA, x):
        pre_op_data = deepcopy(DATA)
        post_op_data = DATA * x
        helper_mat_vec_unchanged_computed_coeffs_are_correct(post_op_data, pre_op_data, op.mul, x)


    ###############  Outer product  ##################
    # NOTE : not implemented => not tested