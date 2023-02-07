# Copyright 2022 Xanadu Quantum Technologies Inc.

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
from scipy.interpolate import interp1d

from mrmustard import settings
from mrmustard.abstract.data import Data
from mrmustard.math import Math

math = Math()


class MatVecData(Data):
    def __init__(self, mat, vec, coeff):
        self.mat = math.atleast_3d(mat)
        self.vec = math.atleast_2d(vec)
        self.coeff = math.atleast_1d(coeff)

    def __add__(self, other: MatVecData):
        if np.allclose(self.mat, other.mat) and np.allclose(self.vec, other.vec):
            return MatVecData(self.mat, self.vec, self.coeff + other.coeff)
        return MatVecData(
            math.concat([self.mat, other.mat], axis=0),
            math.concat([self.vec, other.vec], axis=0),
            math.concat([self.coeff, other.coeff], axis=0),
        )

    def simplify(self):
        to_check = set(range(len(self.mat)))
        removed = set()
        while to_check:
            i = to_check.pop()
            for j in to_check.copy():
                if np.allclose(self.mat[i], self.mat[j]) and np.allclose(self.vec[i], self.vec[j]):
                    self.coeff[i] += self.coeff[j]
                    to_check.remove(j)
                    removed.add(j)
        to_keep = [i for i in range(len(self.mat)) if i not in removed]
        self.mat = self.mat[to_keep]
        self.vec = self.vec[to_keep]
        self.coeff = self.coeff[to_keep]

    def __eq__(self, other):
        return (
            np.allclose(self.mat, other.mat)
            and np.allclose(self.vec, other.vec)
            and np.allclose(self.coeff, other.coeff)
        )

    def __and__(self, other):
        mat = []
        vec = []
        coeff = []
        for c1 in self.mat:
            for c2 in other.mat:
                mat.append(math.block_diag([c1, c2]))
        for m1 in self.mean:
            for m2 in other.mean:
                vec.append(math.concat([m1, m2], axis=-1))
        for c1 in self.coeff:
            for c2 in other.coeff:
                coeff.append(c1 * c2)
        mat = math.astensor(mat)
        vec = math.astensor(vec)
        coeff = math.astensor(coeff)
        return self.__class__(mat, vec, coeff)


class GaussianData(MatVecData):
    def __init__(self, cov=None, mean=None, coeff=None):
        r"""
        Gaussian data: covariance, mean, coefficient.
        Each of these has a batch dimension, and the length of the
        batch dimension is the same for all three.
        These are the parameters of a linear combination of Gaussians,
        which is Gaussian if there is only one contribution for each.
        Each contribution parametrizes the Gaussian function:
        `coeff * exp(-0.5*(x-mean)^T cov^-1 (x-mean))`.
        Args:
            cov (batch, dim, dim): covariance matrices (real symmetric)
            mean  (batch, dim): means (real)
            coeff (batch): coefficients (complex)
        """
        # TODO handle missing data
        # TODO switch to data/kwargs?
        if isinstance(cov, QuadraticPolyData):  # enables GaussianData(quadraticdata)
            poly = cov  # for readability
            inv_A = math.inv(poly.A)
            cov = 2 * inv_A
            mean = 2 * math.solve(poly.A, poly.b)
            coeff = poly.c * math.cast(
                math.exp(0.5 * math.einsum("bca,bcd,bde->bae", mean, cov, mean)), poly.c.dtype
            )
        else:
            super().__init__(cov, mean, coeff)

    @property
    def cov(self):
        return self.mat

    @cov.setter
    def cov(self, value):
        self.mat = value

    @property
    def mean(self):
        return self.vec

    @mean.setter
    def mean(self, value):
        self.vec = value

    def __mul__(self, other):
        if isinstance(other, Number):
            return GaussianData(
                self.cov, self.mean, self.coeff * math.cast(other, self.coeff.dtype)
            )
        elif isinstance(other, GaussianData):
            # cov matrices: c1 (c1 + c2)^-1 c2 for each pair of cov matrices in the batch
            covs = []
            for c1 in self.cov:
                for c2 in other.cov:
                    covs.append(math.matmul(c1, math.solve(c1 + c2, c2)))
            # means: c1 (c1 + c2)^-1 m2 + c2 (c1 + c2)^-1 m1 for each pair of cov matrices in the batch
            means = []
            for c1, m1 in zip(self.cov, self.mean):
                for c2, m2 in zip(other.cov, other.mean):
                    means.append(
                        math.matvec(c1, math.solve(c1 + c2, m2))
                        + math.matvec(c2, math.solve(c1 + c2, m1))
                    )
            cov = math.astensor(covs)
            mean = math.astensor(means)
            coeffs = []
            for c1, m1, c2, m2, c3, m3, co1, co2 in zip(
                self.cov, self.mean, other.cov, other.mean, cov, mean, self.coeff, other.coeff
            ):
                coeffs.append(
                    co1
                    * co2
                    * math.exp(
                        0.5 * math.sum(m1 * math.solve(c1, m1), axes=-1)
                        + 0.5 * math.sum(m2 * math.solve(c2, m2), axes=-1)
                        - 0.5 * math.sum(m3 * math.solve(c3, m3), axes=-1)
                    )
                )

            coeff = math.astensor(coeffs)
            return GaussianData(cov, mean, coeff)
        else:
            raise TypeError(f"Cannot multiply GaussianData with {other.__class__.__qualname__}")


class QuadraticPolyData(MatVecData):
    def __init__(self, A=None, b=None, c=None):
        r"""
        Quadratic Gaussian data: quadratic coefficients, linear coefficients, constant.
        Each of these has a batch dimension, and the batch dimension is the same for all of them.
        They are the parameters of a Gaussian expressed as `c * exp(-x^T A x + x^T b)`.
        Args:
            A (batch, dim, dim): quadratic coefficients
            b (batch, dim): linear coefficients
            c (batch): constant
        """
        if isinstance(A, GaussianData):
            A = -math.inv(A.cov)
            b = math.inv(A.cov) @ A.mean
            c = A.coeff * np.einsum("bca,bcd,bde->bae", A.mean, math.inv(A.cov), A.mean)
        super().__init__(A, b, c)

    @property
    def A(self):
        return self.mat

    @A.setter
    def A(self, value):
        self.mat = value

    @property
    def b(self):
        return self.vec

    @b.setter
    def b(self, value):
        self.vec = value

    def __mul__(self, other):
        if isinstance(
            other, Number
        ):  # TODO: this seems to deal only with the case of self and other being a single gaussian
            return QuadraticPolyData(self.A, self.b, self.c * other)
        elif isinstance(other, QuadraticPolyData):
            return QuadraticPolyData(
                self.A + other.A, self.b + other.b, self.c * other.c
            )  # TODO: invert decomposed covs instead
        else:
            raise TypeError(
                f"Cannot multiply QuadraticPolyData with {other.__class__.__qualname__}"
            )


class SamplesData(Data):
    "First version. Not differentiable. Only works for R^1 -> C^1 functions."
    max_dom_points = settings.DATA_MAX_SAMPLES_1D

    def __init__(self, x, y):
        self.interp_real = interp1d(x, np.real(y))
        self.interp_imag = interp1d(x, np.imag(y))

    def intersect_domains(self, other):
        x = np.union1d(self.domain, other.domain)
        # find intersection of x ranges
        x_min = max(self.domain.min(), other.domain.min())
        x_max = min(self.domain.max(), other.domain.max())
        # keep only the intersection
        x = x[(x >= x_min) & (x <= x_max)]
        return x

    @property
    def domain(self):
        return self.interp_real.x

    @property
    def values(self):
        return self.interp_real.y + 1j * self.interp_imag.y

    def plot(self):
        phase = np.angle(self.values)
        magnitude = np.abs(self.values)
        # convert phase to be between 0 and 1
        phase = (phase + np.pi) / (2 * np.pi)
        fig, ax = plt.subplots()
        ax.scatter(self.domain, magnitude, c=phase, cmap=cm.hsv, marker=".")
        ax.plot(self.domain, magnitude, color="black", linewidth=1)
        return ax

    def resample(self):
        """Resample the domain to have at most max_dom_points points.
        Sample more points where the derivative is large.
        """
        min_, max_ = self.domain.min(), self.domain.max()
        dom = np.linspace(min_, max_, self.max_dom_points)
        real_grad = np.gradient(self.interp_real(dom), dom)
        imag_grad = np.gradient(self.interp_imag(dom), dom)
        dy = np.abs(real_grad - 1j * imag_grad)  # Warning: unverified
        dy = interp1d(dom, dy)
        # we have a budget of max_dom_points,
        # we sample them between x.min() and x.max()
        # using dy as a probability distribution
        a = np.linspace(self.domain.min(), self.domain.max(), 10000)
        x = np.random.choice(
            a=a,
            size=self.max_dom_points,
            p=dy(a) / dy(a).sum(),
        )
        self.interp_real = interp1d(x, self.interp_real(x))
        self.interp_imag = interp1d(x, self.interp_imag(x))

    def __call__(self, x):
        return self.interp_real(x) + 1j * self.interp_imag(x)

    def __add__(self, other):
        if isinstance(other, self.__class__):
            x = self.intersect_domains(other)
            f = SamplesData(x, self(x) + other(x))
        elif isinstance(other, (int, float, complex)):
            x = self.domain
            f = SamplesData(x, self(x) + other)
        else:
            raise TypeError(f"Cannot add {type(self)} and {type(other)}")
        if len(x) > self.max_dom_points:
            f.resample()
        return f

    def __radd__(self, other):
        return self + other

    def __mul__(self, other):
        if isinstance(other, SamplesData):
            x = self.intersect_domains(other)
            f = SamplesData(x, self(x) * other(x))
        elif isinstance(other, (int, float, complex)):
            x = self.domain
            f = SamplesData(x, self(x) * other)
        else:
            raise TypeError(f"Cannot multiply {type(self)} and {type(other)}")
        if len(x) > self.max_dom_points:
            f.resample()
        return f

    def __rmul__(self, other):
        return self * other

    def __neg__(self):
        return SamplesData(self.domain, -self.interp_real.y - 1j * self.interp_imag.y)

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return other + (-self)

    def __truediv__(self, other):
        if isinstance(other, SamplesData):
            x = self.intersect_domains(other)
            f = SamplesData(x, self(x) / other(x))
        elif isinstance(other, (int, float, complex)):
            x = self.domain
            f = SamplesData(x, self(x) / other)
        if len(x) > self.max_dom_points:
            f.resample()
        return f

    def __rtruediv__(self, other):
        if isinstance(other, (int, float, complex)):
            x = self.domain
            return SamplesData(x, other / self(x))

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        if method == "__call__":
            x = inputs[0].domain
            y = ufunc(*(input(x) for input in inputs), **kwargs)
            return SamplesData(x, y)
        else:
            raise NotImplementedError


def AutoData(**kwargs):
    r"""Automatically choose the data type based on the arguments.
    If the arguments contain any combination of 'cov', 'mean', 'coeff' then it is GaussianData.
    If the arguments contain any combination of 'A', 'b', 'c' then it is QuadraticPolyData.
    If the arguments contain 'x' and 'y' then it is SamplesData.

    """
    if "cov" in kwargs or "mean" in kwargs or "coeff" in kwargs:
        return GaussianData(**kwargs)
    elif "A" in kwargs or "b" in kwargs or "c" in kwargs:
        return QuadraticPolyData(**kwargs)
    elif "x" in kwargs and "y" in kwargs:
        return SamplesData(**kwargs)
    else:
        raise TypeError("Cannot automatically choose data type from the given arguments")