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

from abc import ABC

class Data(ABC):

    def __init__(self) -> None:
        super().__init__()

    
    @abstractmethod
    def __eq__():
        pass


    @abstractmethod
    def __add__():
        pass


    @abstractmethod
    def __sub__():
        pass


    @abstractmethod
    def __truediv__():
        pass


    @abstractmethod
    def __rmul__():
        pass


    @abstractmethod
    def __neg__():
        pass


    @abstractmethod
    def __and__():
        pass


    @abstractmethod
    def simplify():
        pass

