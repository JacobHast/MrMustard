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

import numpy as np
import pytest

from mrmustard.lab.representations.wavefunctionq import WaveFunctionQ


class TestWaveFunctionQThrowErrors():

    wfq = WaveFunctionQ(qs=np.random(3) , array = np.random.random((3,3)))
    

    def test_number_means_with_error(self):
        with self.assertRaises(NotImplementedError):
            self.wfq.number_means
    

    def test_number_cov_with_error(self):
        with self.assertRaises(NotImplementedError):
            self.wfq.number_cov
    

    def test_number_variance_with_error(self):
        with self.assertRaises(NotImplementedError):
            self.wfq.number_variances