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

"""This module contains the implementation of the :class:`State` class."""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import warnings

from typing import (
    TYPE_CHECKING,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from matplotlib import cm

from mrmustard import settings
from mrmustard.math import Math
from mrmustard.math.parameters import Constant, Variable
from mrmustard.physics import bargmann, fock, gaussian
from mrmustard.utils.typing import (
    ComplexMatrix,
    ComplexTensor,
    ComplexVector,
    RealMatrix,
    RealTensor,
    RealVector,
)
from mrmustard.physics.wigner import wigner_discretized


if TYPE_CHECKING:
    from .transformation import Transformation

math = Math()


# pylint: disable=too-many-instance-attributes
class State:  # pylint: disable=too-many-public-methods
    r"""Base class for quantum states."""

    def __init__(
        self,
        cov: RealMatrix = None,
        means: RealVector = None,
        eigenvalues: RealVector = None,
        symplectic: RealMatrix = None,
        ket: ComplexTensor = None,
        dm: ComplexTensor = None,
        modes: Sequence[int] = None,
        cutoffs: Sequence[int] = None,
        _norm: float = 1.0,
    ):
        r"""Initializes the state.

        Supply either:
            * a covariance matrix and means vector
            * an eigenvalues array and symplectic matrix
            * a fock representation (ket or dm)

        Args:
            cov (Matrix): the covariance matrix
            means (Vector): the means vector
            eigenvalues (Tensor): the eigenvalues of the covariance matrix
            symplectic (Matrix): the symplectic matrix mapping the thermal state with given eigenvalues to this state
            fock (Tensor): the Fock representation
            modes (optional, Sequence[int]): the modes in which the state is defined
            cutoffs (Sequence[int], default=None): set to force the cutoff dimensions of the state
            _norm (float, default=1.0): the norm of the state. Warning: only set if you know what you are doing.

        """
        self._purity = None
        self._fock_probabilities = None
        self._cutoffs = cutoffs
        self._cov = cov
        self._means = means
        self._eigenvalues = eigenvalues
        self._symplectic = symplectic
        self._ket = ket
        self._dm = dm
        self._norm = _norm
        if cov is not None and means is not None:
            self.is_gaussian = True
            self.is_hilbert_vector = np.allclose(gaussian.purity(self.cov), 1.0, atol=1e-6)
            self.num_modes = cov.shape[-1] // 2
        elif eigenvalues is not None and symplectic is not None:
            self.is_gaussian = True
            self.is_hilbert_vector = np.allclose(eigenvalues, 2.0 / settings.HBAR)
            self.num_modes = symplectic.shape[-1] // 2
        elif ket is not None or dm is not None:
            self.is_gaussian = False
            self.is_hilbert_vector = ket is not None
            self.num_modes = len(ket.shape) if ket is not None else len(dm.shape) // 2
            self._purity = 1.0 if ket is not None else None
        else:
            raise ValueError(
                "State must be initialized with either a covariance matrix and means vector, an eigenvalues array and symplectic matrix, or a fock representation"
            )
        self._modes = modes
        if modes is not None:
            assert (
                len(modes) == self.num_modes
            ), f"Number of modes supplied ({len(modes)}) must match the representation dimension {self.num_modes}"

    def _add_parameter(self, parameter: Union[Constant, Variable]):
        r"""
        Adds a parameter to a state.

        Args:
            parameter: The parameter to add.
        """
        if not getattr(self, "_parameter_set", None):
            msg = "Cannot add a parameter to a state with no parameter set."
            raise ValueError(msg)
        self.parameter_set.add_parameter(parameter)
        self.__dict__[parameter.name] = parameter

    @property
    def parameter_set(self):
        r"""
        The set of parameters for this state.
        """
        return getattr(self, "_parameter_set", None)

    @property
    def modes(self):
        r"""Returns the modes of the state."""
        if self._modes is None:
            return list(range(self.num_modes))
        return self._modes

    def indices(self, modes) -> Union[Tuple[int], int]:
        r"""Returns the indices of the given modes.

        Args:
            modes (Sequence[int] or int): the modes or mode

        Returns:
            Tuple[int] or int: a tuple of indices of the given modes or the single index of a single mode
        """
        if isinstance(modes, int):
            return self.modes.index(modes)
        return tuple(self.modes.index(m) for m in modes)

    @property
    def purity(self) -> float:
        """Returns the purity of the state."""
        if self._purity is None:
            if self.is_gaussian:
                self._purity = gaussian.purity(self.cov)
            else:
                self._purity = fock.purity(self._dm)
        return self._purity

    @property
    def is_mixed(self):
        r"""Returns whether the state is mixed."""
        return not self.is_pure

    @property
    def is_pure(self):
        r"""Returns ``True`` if the state is pure and ``False`` otherwise."""
        return np.isclose(self.purity, 1.0, atol=1e-6)

    @property
    def means(self) -> Optional[RealVector]:
        r"""Returns the means vector of the state."""
        return self._means

    @property
    def cov(self) -> Optional[RealMatrix]:
        r"""Returns the covariance matrix of the state."""
        return self._cov

    @property
    def number_stdev(self) -> RealVector:
        r"""Returns the square root of the photon number variances (standard deviation) in each mode."""
        if self.is_gaussian:
            return math.sqrt(math.diag_part(self.number_cov))

        return math.sqrt(
            fock.number_variances(self.fock, is_dm=len(self.fock.shape) == self.num_modes * 2)
        )

    @property
    def cutoffs(self) -> List[int]:
        r"""Returns the Hilbert space dimension of each mode."""
        if self._cutoffs is None:
            if self._ket is None and self._dm is None:
                self._cutoffs = fock.autocutoffs(
                    self.cov, self.means, settings.AUTOCUTOFF_PROBABILITY
                )
            else:
                self._cutoffs = [
                    int(c)
                    for c in (
                        self._ket.shape
                        if self._ket is not None
                        else self._dm.shape[: self.num_modes]
                    )
                ]
        return self._cutoffs

    @property
    def shape(self) -> List[int]:
        r"""Returns the shape of the state, accounting for ket/dm representation.

        If the state is in Gaussian representation, the shape is inferred from
        the first two moments of the number operator.
        """
        # NOTE: if we initialize State(dm=pure_dm), self.fock returns the dm, which does not have shape self.cutoffs
        return self.cutoffs if self.is_hilbert_vector else self.cutoffs + self.cutoffs

    @property
    def fock(self) -> ComplexTensor:
        r"""Returns the Fock representation of the state."""
        if self._dm is None and self._ket is None:
            _fock = fock.wigner_to_fock_state(
                self.cov,
                self.means,
                shape=self.shape,
                return_dm=not self.is_hilbert_vector,
            )
            if self.is_mixed:
                self._dm = _fock
                self._ket = None
            else:
                self._ket = _fock
                self._dm = None
        return self._ket if self._ket is not None else self._dm

    @property
    def number_means(self) -> RealVector:
        r"""Returns the mean photon number for each mode."""
        if self.is_gaussian:
            return gaussian.number_means(self.cov, self.means)

        return fock.number_means(tensor=self.fock, is_dm=self.is_mixed)

    @property
    def number_cov(self) -> RealMatrix:
        r"""Returns the complete photon number covariance matrix."""
        if not self.is_gaussian:
            raise NotImplementedError("number_cov not yet implemented for non-gaussian states")

        return gaussian.number_cov(self.cov, self.means)

    @property
    def norm(self) -> float:
        r"""Returns the norm of the state."""
        if self.is_gaussian:
            return self._norm
        return fock.norm(self.fock, not self.is_hilbert_vector)

    @property
    def probability(self) -> float:
        r"""Returns the probability of the state."""
        norm = self.norm
        if self.is_pure and self._ket is not None:
            return norm**2
        return norm

    def ket(
        self,
        cutoffs: List[int] = None,
        max_prob: float = 1.0,
        max_photons: int = None,
    ) -> Optional[ComplexTensor]:
        r"""Returns the ket of the state in Fock representation or ``None`` if the state is mixed.

        Args:
            cutoffs List[int or None]: The cutoff dimensions for each mode. If a mode cutoff is
                ``None``, it's guessed automatically.
            max_prob (float): The maximum probability of the state. Defaults to 1.0.
                (used to stop the calculation of the amplitudes early)
            max_photons (int): The maximum number of photons in the state, summing over all modes
                (used to stop the calculation of the amplitudes early)

        Returns:
            Tensor: the ket
        """
        if self.is_mixed:
            return None

        if cutoffs is None:
            cutoffs = self.cutoffs
        else:
            cutoffs = [c if c is not None else self.cutoffs[i] for i, c in enumerate(cutoffs)]

        # TODO: shouldn't we check if trainable instead? that's when we want to recompute fock
        if self.is_gaussian:
            self._ket = fock.wigner_to_fock_state(
                self.cov,
                self.means,
                shape=cutoffs,
                return_dm=False,
                max_prob=max_prob,
                max_photons=max_photons,
            )
        else:  # only fock representation is available
            if self._ket is None:
                # if state is pure and has a density matrix, calculate the ket
                if self.is_pure:
                    self._ket = fock.dm_to_ket(self._dm)
            current_cutoffs = [int(s) for s in self._ket.shape]
            if cutoffs != current_cutoffs:
                paddings = [(0, max(0, new - old)) for new, old in zip(cutoffs, current_cutoffs)]
                if any(p != (0, 0) for p in paddings):
                    padded = fock.math.pad(self._ket, paddings, mode="constant")
                else:
                    padded = self._ket
                return padded[tuple(slice(s) for s in cutoffs)]
        return self._ket[tuple(slice(s) for s in cutoffs)]

    def dm(self, cutoffs: Optional[List[int]] = None) -> ComplexTensor:
        r"""Returns the density matrix of the state in Fock representation.

        Args:
            cutoffs List[int]: The cutoff dimensions for each mode. If a mode cutoff is ``None``,
                it's automatically computed.

        Returns:
            Tensor: the density matrix
        """
        if cutoffs is None:
            cutoffs = self.cutoffs
        else:
            cutoffs = [c if c is not None else self.cutoffs[i] for i, c in enumerate(cutoffs)]
        if self.is_pure:
            ket = self.ket(cutoffs=cutoffs)
            if ket is not None:
                return fock.ket_to_dm(ket)
        else:
            if self.is_gaussian:
                self._dm = fock.wigner_to_fock_state(
                    self.cov, self.means, shape=cutoffs + cutoffs, return_dm=True
                )
            elif cutoffs != (current_cutoffs := list(self._dm.shape[: self.num_modes])):
                paddings = [(0, max(0, new - old)) for new, old in zip(cutoffs, current_cutoffs)]
                if any(p != (0, 0) for p in paddings):
                    padded = fock.math.pad(self._dm, paddings + paddings, mode="constant")
                else:
                    padded = self._dm
                return padded[tuple(slice(s) for s in cutoffs + cutoffs)]
        return self._dm[tuple(slice(s) for s in cutoffs + cutoffs)]

    def fock_probabilities(self, cutoffs: Sequence[int]) -> RealTensor:
        r"""Returns the probabilities in Fock representation.

        If the state is pure, they are the absolute value squared of the ket amplitudes.
        If the state is mixed they are the multi-dimensional diagonals of the density matrix.

        Args:
            cutoffs List[int]: the cutoff dimensions for each mode

        Returns:
            Tensor: the probabilities
        """
        if self._fock_probabilities is None:
            if self.is_mixed:
                dm = self.dm(cutoffs=cutoffs)
                self._fock_probabilities = fock.dm_to_probs(dm)
            else:
                ket = self.ket(cutoffs=cutoffs)
                self._fock_probabilities = fock.ket_to_probs(ket)
        return self._fock_probabilities

    def primal(self, other: Union[State, Transformation]) -> State:
        r"""Returns the post-measurement state after ``other`` is projected onto ``self``.

        ``other << self`` is other projected onto ``self``.

        If ``other`` is a ``Transformation``, it returns the dual of the transformation applied to
        ``self``: ``other << self`` is like ``self >> other^dual``.

        Note that the returned state is not normalized. To normalize a state you can use
        ``mrmustard.physics.normalize``.
        """
        # import pdb

        # pdb.set_trace()
        if isinstance(other, State):
            return self._project_onto_state(other)
        try:
            return other.dual(self)
        except AttributeError as e:
            raise TypeError(
                f"Cannot apply {other.__class__.__qualname__} to {self.__class__.__qualname__}"
            ) from e

    def _project_onto_state(self, other: State) -> Union[State, float]:
        """If states are gaussian use generaldyne measurement, else use
        the states' Fock representation."""

        # if both states are gaussian
        if self.is_gaussian and other.is_gaussian:
            return self._project_onto_gaussian(other)

        # either self or other is not gaussian
        return self._project_onto_fock(other)

    def _project_onto_fock(self, other: State) -> Union[State, float]:
        """Returns the post-measurement state of the projection between two non-Gaussian
        states on the remaining modes or the probability of the result. When doing homodyne sampling,
        returns the post-measurement state or the measument outcome if no modes remain.

        Args:
            other (State): state being projected onto self

        Returns:
            State or float: returns the conditional state on the remaining modes
                or the probability.
        """
        remaining_modes = list(set(other.modes) - set(self.modes))

        out_fock = self._contract_with_other(other)
        if len(remaining_modes) > 0:
            return (
                State(dm=out_fock, modes=remaining_modes)
                if other.is_mixed or self.is_mixed
                else State(ket=out_fock, modes=remaining_modes)
            )

        # return the probability (norm) of the state when there are no modes left
        return (
            fock.math.abs(out_fock) ** 2
            if other.is_pure and self.is_pure
            else fock.math.abs(out_fock)
        )

    def _contract_with_other(self, other):
        other_cutoffs = [
            None if m not in self.modes else other.cutoffs[other.indices(m)] for m in other.modes
        ]
        if hasattr(self, "_preferred_projection"):
            out_fock = self._preferred_projection(other, other.indices(self.modes))
        else:
            # matching other's cutoffs
            self_cutoffs = [other.cutoffs[other.indices(m)] for m in self.modes]
            out_fock = fock.contract_states(
                stateA=other.ket(other_cutoffs) if other.is_pure else other.dm(other_cutoffs),
                stateB=self.ket(self_cutoffs) if self.is_pure else self.dm(self_cutoffs),
                a_is_dm=other.is_mixed,
                b_is_dm=self.is_mixed,
                modes=other.indices(self.modes),
                normalize=self._normalize if hasattr(self, "_normalize") else False,
            )

        return out_fock

    def _project_onto_gaussian(self, other: State) -> Union[State, float]:
        """Returns the result of a generaldyne measurement given that states ``self`` and
        ``other`` are gaussian.

        Args:
            other (State): gaussian state being projected onto self

        Returns:
            State or float: returns the output conditional state on the remaining modes
                or the probability.
        """
        # here `self` is the measurement device state and `other` is the incoming state
        # being projected onto the measurement state
        remaining_modes = list(set(other.modes) - set(self.modes))

        _, probability, new_cov, new_means = gaussian.general_dyne(
            other.cov,
            other.means,
            self.cov,
            self.means,
            self.modes,
        )

        if len(remaining_modes) > 0:
            return State(
                means=new_means,
                cov=new_cov,
                modes=remaining_modes,
                _norm=probability if not getattr(self, "_normalize", False) else 1.0,
            )

        return probability

    def __iter__(self) -> Iterable[State]:
        """Iterates over the modes and their corresponding tensors."""
        return (self.get_modes(i) for i in range(self.num_modes))

    def __and__(self, other: State) -> State:
        r"""Concatenates two states."""
        if not self.is_gaussian or not other.is_gaussian:  # convert all to fock now
            # TODO: would be more efficient if we could keep pure states as kets
            if self.is_mixed or other.is_mixed:
                self_fock = self.dm()
                other_fock = other.dm()
                dm = fock.math.tensordot(self_fock, other_fock, [[], []])
                # e.g. self has shape [1,3,1,3] and other has shape [2,2]
                # we want self & other to have shape [1,3,2,1,3,2]
                # before transposing shape is [1,3,1,3]+[2,2]
                self_idx = list(range(len(self_fock.shape)))
                other_idx = list(range(len(self_idx), len(self_idx) + len(other_fock.shape)))
                return State(
                    dm=math.transpose(
                        dm,
                        self_idx[: len(self_idx) // 2]
                        + other_idx[: len(other_idx) // 2]
                        + self_idx[len(self_idx) // 2 :]
                        + other_idx[len(other_idx) // 2 :],
                    ),
                    modes=self.modes + [m + max(self.modes) + 1 for m in other.modes],
                )
            # else, all states are pure
            self_fock = self.ket()
            other_fock = other.ket()
            return State(
                ket=fock.math.tensordot(self_fock, other_fock, [[], []]),
                modes=self.modes + [m + max(self.modes) + 1 for m in other.modes],
            )
        cov = gaussian.join_covs([self.cov, other.cov])
        means = gaussian.join_means([self.means, other.means])
        return State(
            cov=cov,
            means=means,
            modes=self.modes + [m + self.num_modes for m in other.modes],
        )

    def __getitem__(self, item) -> State:
        "setting the modes of a state (same API of `Transformation`)"
        if isinstance(item, int):
            item = [item]
        elif isinstance(item, Iterable):
            item = list(item)
        else:
            raise TypeError("item must be int or iterable")
        if len(item) != self.num_modes:
            raise ValueError(
                f"there are {self.num_modes} modes (item has {len(item)} elements, perhaps you're looking for .get_modes()?)"
            )
        self._modes = item
        return self

    def bargmann(self, numpy=False) -> Optional[tuple[ComplexMatrix, ComplexVector, complex]]:
        r"""Returns the Bargmann representation of the state.
        If numpy=True, returns the numpy arrays instead of the backend arrays.
        """
        if self.is_gaussian:
            if self.is_pure:
                A, B, C = bargmann.wigner_to_bargmann_psi(self.cov, self.means)
            else:
                A, B, C = bargmann.wigner_to_bargmann_rho(self.cov, self.means)
        else:
            return None
        if numpy:
            return math.asnumpy(A), math.asnumpy(B), math.asnumpy(C)
        return A, B, C

    def get_modes(self, item) -> State:
        r"""Returns the state on the given modes."""
        if isinstance(item, int):
            item = [item]
        elif isinstance(item, Iterable):
            item = list(item)
        else:
            raise TypeError("item must be int or iterable")

        if item == self.modes:
            return self

        if not set(item) & set(self.modes):
            raise ValueError(
                f"Failed to request modes {item} for state {self} on modes {self.modes}."
            )
        item_idx = [self.modes.index(m) for m in item]
        if self.is_gaussian:
            cov, _, _ = gaussian.partition_cov(self.cov, item_idx)
            means, _ = gaussian.partition_means(self.means, item_idx)
            return State(cov=cov, means=means, modes=item)

        fock_partitioned = fock.trace(self.dm(self.cutoffs), keep=item_idx)
        return State(dm=fock_partitioned, modes=item)

    # TODO: refactor
    def __eq__(self, other) -> bool:  # pylint: disable=too-many-return-statements
        r"""Returns whether the states are equal."""
        if self.num_modes != other.num_modes:
            return False
        if not np.isclose(self.purity, other.purity, atol=1e-6):
            return False
        if self.is_gaussian and other.is_gaussian:
            if not np.allclose(self.means, other.means, atol=1e-6):
                return False
            if not np.allclose(self.cov, other.cov, atol=1e-6):
                return False
            return True
        try:
            return np.allclose(
                self.ket(cutoffs=other.cutoffs),
                other.ket(cutoffs=other.cutoffs),
                atol=1e-6,
            )
        except TypeError:
            return np.allclose(
                self.dm(cutoffs=other.cutoffs),
                other.dm(cutoffs=other.cutoffs),
                atol=1e-6,
            )

    def __rshift__(self, other: Transformation) -> State:
        r"""Applies other (a Transformation) to self (a State), e.g., ``Coherent(x=0.1) >> Sgate(r=0.1)``."""
        if issubclass(other.__class__, State):
            raise TypeError(
                f"Cannot apply {other.__class__.__qualname__} to a state. Are you looking for the << operator?"
            )
        return other.primal(self)

    def __lshift__(self, other: State):
        r"""Implements projection onto a state or the dual transformation applied on a state.

        E.g., ``self << other`` where other is a ``State`` and ``self`` is either a ``State`` or a ``Transformation``.
        """
        return other.primal(self)

    def __add__(self, other: State):
        r"""Implements a mixture of states (only available in fock representation for the moment)."""
        if not isinstance(other, State):
            raise TypeError(f"Cannot add {other.__class__.__qualname__} to a state")
        warnings.warn("mixing states forces conversion to fock representation", UserWarning)
        return State(dm=self.dm(self.cutoffs) + other.dm(self.cutoffs))

    def __rmul__(self, other):
        r"""Implements multiplication by a scalar from the left.

        E.g., ``0.5 * psi``.
        """
        if self.is_gaussian:
            warnings.warn(
                "scalar multiplication forces conversion to fock representation",
                UserWarning,
            )
            if self.is_pure:
                return State(ket=self.ket() * other)
            return State(dm=self.dm() * other)
        if self._dm is not None:
            return State(dm=self.dm() * other, modes=self.modes)
        if self._ket is not None:
            return State(ket=self.ket() * other, modes=self.modes)
        raise ValueError("No fock representation available")

    def __truediv__(self, other):
        r"""Implements division by a scalar from the left.

        E.g. ``psi / 0.5``
        """
        if self.is_gaussian:
            warnings.warn("scalar division forces conversion to fock representation", UserWarning)
            if self.is_pure:
                return State(ket=self.ket() / other)
            return State(dm=self.dm() / other)
        if self._dm is not None:
            return State(dm=self.dm() / other, modes=self.modes)
        if self._ket is not None:
            return State(ket=self.ket() / other, modes=self.modes)
        raise ValueError("No fock representation available")

    @staticmethod
    def _format_probability(prob: float) -> str:
        if prob < 0.001:
            return f"{100*prob:.3e} %"
        else:
            return f"{prob:.3%}"

    def _repr_markdown_(self):
        table = (
            f"#### {self.__class__.__qualname__}\n\n"
            + "| Purity | Probability | Num modes | Bosonic size | Gaussian | Fock |\n"
            + "| :----: | :----: | :----: | :----: | :----: | :----: |\n"
            + f"| {self.purity :.2e} | "
            + self._format_probability(self.probability)
            + f" | {self.num_modes} | {'1' if self.is_gaussian else 'N/A'} | {'✅' if self.is_gaussian else '❌'} | {'✅' if self._ket is not None or self._dm is not None else '❌'} |"
        )

        if self.num_modes == 1:
            mikkel_plot(math.asnumpy(self.dm(cutoffs=self.cutoffs)))

        if settings.DEBUG:
            detailed_info = f"\ncov={repr(self.cov)}\n" + f"means={repr(self.means)}\n"
            return f"{table}\n{detailed_info}"

        return table


def mikkel_plot(
    rho: np.ndarray,
    xbounds: Tuple[int] = (-6, 6),
    ybounds: Tuple[int] = (-6, 6),
    **kwargs,
):  # pylint: disable=too-many-statements
    """Plots the Wigner function of a state given its density matrix.

    Args:
        rho (np.ndarray): density matrix of the state
        xbounds (Tuple[int]): range of the x axis
        ybounds (Tuple[int]): range of the y axis

    Keyword args:
        resolution (int): number of points used to calculate the wigner function
        xticks (Tuple[int]): ticks of the x axis
        xtick_labels (Optional[Tuple[str]]): labels of the x axis; if None uses default formatter
        yticks (Tuple[int]): ticks of the y axis
        ytick_labels (Optional[Tuple[str]]): labels of the y axis; if None uses default formatter
        grid (bool): whether to display the grid
        cmap (matplotlib.colormap): colormap of the figure

    Returns:
        tuple: figure and axes
    """

    plot_args = {
        "resolution": 200,
        "xticks": (-5, 0, 5),
        "xtick_labels": None,
        "yticks": (-5, 0, 5),
        "ytick_labels": None,
        "grid": False,
        "cmap": cm.RdBu,
    }
    plot_args.update(kwargs)

    if plot_args["xtick_labels"] is None:
        plot_args["xtick_labels"] = plot_args["xticks"]
    if plot_args["ytick_labels"] is None:
        plot_args["ytick_labels"] = plot_args["yticks"]

    q, ProbX = fock.quadrature_distribution(rho)
    p, ProbP = fock.quadrature_distribution(rho, np.pi / 2)

    xvec = np.linspace(*xbounds, plot_args["resolution"])
    pvec = np.linspace(*ybounds, plot_args["resolution"])
    W, X, P = wigner_discretized(rho, xvec, pvec)

    ### PLOTTING ###

    fig, ax = plt.subplots(
        2,
        2,
        figsize=(6, 6),
        gridspec_kw={"width_ratios": [2, 1], "height_ratios": [1, 2]},
    )
    plt.subplots_adjust(wspace=0.05, hspace=0.05)

    # Wigner function
    ax[1][0].contourf(X, P, W, 120, cmap=plot_args["cmap"], vmin=-abs(W).max(), vmax=abs(W).max())
    ax[1][0].set_xlabel("$x$", fontsize=12)
    ax[1][0].set_ylabel("$p$", fontsize=12)
    ax[1][0].get_xaxis().set_ticks(plot_args["xticks"])
    ax[1][0].xaxis.set_ticklabels(plot_args["xtick_labels"])
    ax[1][0].get_yaxis().set_ticks(plot_args["yticks"])
    ax[1][0].yaxis.set_ticklabels(plot_args["ytick_labels"], rotation="vertical", va="center")
    ax[1][0].tick_params(direction="in")
    ax[1][0].set_xlim(xbounds)
    ax[1][0].set_ylim(ybounds)
    ax[1][0].grid(plot_args["grid"])

    # X quadrature probability distribution
    ax[0][0].fill(q, ProbX, color=plot_args["cmap"](0.5))
    ax[0][0].plot(q, ProbX, color=plot_args["cmap"](0.8))
    ax[0][0].get_xaxis().set_ticks(plot_args["xticks"])
    ax[0][0].xaxis.set_ticklabels([])
    ax[0][0].get_yaxis().set_ticks([])
    ax[0][0].tick_params(direction="in")
    ax[0][0].set_ylabel("Prob($x$)", fontsize=12)
    ax[0][0].set_xlim(xbounds)
    ax[0][0].set_ylim([0, 1.1 * max(ProbX)])
    ax[0][0].grid(plot_args["grid"])

    # P quadrature probability distribution
    ax[1][1].fill(ProbP, p, color=plot_args["cmap"](0.5))
    ax[1][1].plot(ProbP, p, color=plot_args["cmap"](0.8))
    ax[1][1].get_xaxis().set_ticks([])
    ax[1][1].get_yaxis().set_ticks(plot_args["yticks"])
    ax[1][1].yaxis.set_ticklabels([])
    ax[1][1].tick_params(direction="in")
    ax[1][1].set_xlabel("Prob($p$)", fontsize=12)
    ax[1][1].set_xlim([0, 1.1 * max(ProbP)])
    ax[1][1].set_ylim(ybounds)
    ax[1][1].grid(plot_args["grid"])

    # Density matrix
    ax[0][1].matshow(abs(rho), cmap=plot_args["cmap"], vmin=-abs(rho).max(), vmax=abs(rho).max())
    ax[0][1].set_title(r"abs($\rho$)", fontsize=12)
    ax[0][1].tick_params(direction="in")
    ax[0][1].get_xaxis().set_ticks([])
    ax[0][1].get_yaxis().set_ticks([])
    ax[0][1].set_aspect("auto")
    ax[0][1].set_ylabel(f"cutoff = {len(rho)}", fontsize=12)
    ax[0][1].yaxis.set_label_position("right")

    return fig, ax


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

"""This module contains the implementation of the :class:`State` class."""

from __future__ import annotations

import warnings
from typing import (
    TYPE_CHECKING,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
import copy

from mrmustard import settings
from mrmustard.math import Math
from mrmustard.physics import fock, gaussian
from mrmustard.lab.representations.representation import Representation
from mrmustard.lab.representations.fock_dm import FockDM
from mrmustard.lab.representations.fock_ket import FockKet
from mrmustard.lab.representations.wigner_ket import WignerKet
from mrmustard.lab.representations.wigner_dm import WignerDM
from mrmustard.lab.representations.wavefunctionq_ket import WaveFunctionQKet
from mrmustard.lab.representations.wavefunctionq_dm import WaveFunctionQDM
from mrmustard.lab.representations.converter import Converter
from mrmustard.typing import (
    ComplexMatrix,
    ComplexTensor,
    ComplexVector,
    RealMatrix,
    RealTensor,
    RealVector,
)
from mrmustard.utils import graphics

if TYPE_CHECKING:
    from .transformation import Transformation

math = Math()
converter = Converter()


class SafeProperty:
    r"""
    A descriptor that catches AttributeError exceptions in a getter method
    and raises a new AttributeError with a custom message.

    Usage:

    @SafeProperty
    def some_property(self):
        return self.some_attribute
    """

    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        try:
            return self.getter(instance)
        except AttributeError:
            raise AttributeError("Property unavailable in the current representation.") from None


# pylint: disable=too-many-instance-attributes
class State:  # pylint: disable=too-many-public-methods
    r"""Base class for quantum states."""

    def __init__(
        self,
        A=None,
        b=None,
        c=None,
        cov=None,
        means=None,
        fock_array=None,
        qs=None,
        wf_q_array=None,
        representation=None,
        modes=None,
    ):
        if A is not None and b is not None and c is not None:
            self._from_Abc(A, b, c)  # init Fock-Bargmann representation
        elif cov is not None and means is not None:
            self._from_cov_means(cov, means)  # init Wigner representation
        elif fock_array is not None:
            self._from_fock_array(fock_array)  # init Fock representation
        elif qs is not None and wf_q_array is not None:
            self._from_wf_q_array(qs, wf_q_array)  # init q-wavefunction representation
        elif representation is not None:
            self.representation = representation
        else:
            raise ValueError(
                f"A state must be initialized with (A,b,c) or (cov, means) or `fock_array` or (qs, wf_q_array)."
            )

        # TODO: this attribute modes is linked to the Circuit. Need to be modified afterwards.
        self.num_modes = self.representation.num_modes

        if modes is not None:  # TODO: will be refactored with CircuitPart
            self._modes = modes
            assert (
                len(modes) == self.num_modes
            ), f"Number of modes supplied ({len(modes)}) must match the representation dimension {self.num_modes}"

    def _from_Abc(self, A, b, c):
        raise NotImplementedError("Initialize a state using Ket or DM class.")

    def _from_cov_means(self, cov, means):
        raise NotImplementedError("Initialize a state using Ket or DM class.")

    def _from_fock_array(self, fock_array):
        raise NotImplementedError("Initialize a state using Ket or DM class.")

    def _from_wf_q_array(self, wf_q_array):
        raise NotImplementedError("Initialize a state using Ket or DM class.")

    def _from_wf_p_array(self, wf_p_array):
        raise NotImplementedError("Initialize a state using Ket or DM class.")

    def is_wigner(self):
        return issubclass(self.representation, (WignerKet, WignerDM))

    def is_fock(self):
        return issubclass(self.representation, (FockKet, FockDM))

    def is_wavefunctionq(self):
        return issubclass(self.representation, (WaveFunctionQKet, WaveFunctionQDM))

    def is_bargmann(self):
        return issubclass(self.representation, (BargmannKet, BargmannDM))

    # def __init__(  # TODO: remove and leave only init in Ket and DM
    #     self,
    #     cov: RealMatrix = None,
    #     means: RealVector = None,
    #     symplectic: RealMatrix = None,
    #     displacement: RealVector = None,
    #     fock: ComplexTensor = None,
    #     qs: RealVector = None,
    #     wavefunctionq: RealVector = None,
    #     modes: Sequence[int] = None,
    #     flag_ket: bool = None,
    #     representation: Representation = None,
    # ):
    #     r"""Initializes the state.

    #     Supply either:
    #         * a covariance matrix and means vector
    #         * a fock representation (ket or dm)
    #         * a quadrature variable vector and corresponding wavefunction samples
    #     together with the flag_ket to indicate the nature of the state.
    #     Or supply simply with the Representation Class.

    #     Args:
    #         cov (Matrix): the covariance matrix
    #         means (Vector): the means vector
    #         symplectic (Matrix): the symplectic matrix
    #         displacement (Vector): the displacement vector
    #         fock (Tensor): the Fock representation
    #         qs (Vector): the point value for corresponding q-wavefunction
    #         wavefunctionq (Vector): the value of the point of the q-wavefunction
    #         flag_ket (boolean): whether this state is a ket (pure) or a density matrix (mixed)
    #         representation (Representation): the Representation Class contains all information about the state
    #     """
    #     # Case 0: All data of the state is wrapped inside one of the Representation classes
    #     if representation:
    #         self.representation = representation
    #     else:
    #         # Case 1: Wigner representation #TODO: add coeff?
    #         if cov is not None and means is not None and flag_ket is not None:
    #             self.representation = WignerDM(cov, means)
    #         elif symplectic is not None and displacement is not None and flag_ket:
    #             self.representation = WignerKet(symplectic, displacement)
    #         # Case 2: Fock representation
    #         elif fock is not None and flag_ket is not None:
    #             if flag_ket:
    #                 self.representation = FockKet(fock)
    #             else:
    #                 self.representation = FockDM(fock)
    #         # Case 3: q-Wavefunction representation
    #         elif qs is not None and wavefunctionq is not None and flag_ket is not None:
    #             if flag_ket:
    #                 self.representation = WaveFunctionQKet(qs, wavefunctionq)
    #             else:
    #                 self.representation = WaveFunctionQDM(qs, wavefunctionq)
    #         else:
    #             raise ValueError(
    #                 "State must be initialized with either a wrapped Representation class, a covariance matrix and means vector, a fock representation, a point-wise wavefunction with its point values and the flag_ket."
    #             )

    @property
    def modes(self):  # will be updated from TN project, also modes in init.
        r"""Returns the modes of the state."""
        if self._modes is None:
            return list(range(self.representation.num_modes))
        return self._modes

    def indices(self, modes) -> Union[Tuple[int], int]:
        r"""Returns the indices of the given modes.

        Args:
            modes (Sequence[int] or int): the modes or mode

        Returns:
            Tuple[int] or int: a tuple of indices of the given modes or the single index of a single mode
        """
        if isinstance(modes, int):
            return self.modes.index(modes)
        return tuple(self.modes.index(m) for m in modes)

    @property
    def purity(self) -> float:  # can override in Ket
        r"""Returns the purity of the state."""
        return self.representation.purity

    @property
    def is_mixed(self):
        r"""Returns whether the state is mixed."""
        return not self.is_pure

    @property
    def is_pure(self):
        r"""Returns whether the state is pure."""
        return np.isclose(self.purity, 1.0, atol=1e-9)

    @SafeProperty
    def means(self) -> Optional[RealVector]:
        r"""Returns the means vector of the state."""
        return self.representation.data.means

    @SafeProperty
    def cov(self) -> Optional[RealMatrix]:  # override in Ket
        r"""Returns the covariance matrix of the state."""
        return self.representation.data.cov

    @property
    def number_stdev(self) -> RealVector:
        r"""Returns the square root of the photon number variances (standard deviation) in each mode."""
        return self.representation.number_stdev()

    @property  # NOTE: this is going to become ambiguous when each wire can have a different representation
    def cutoffs(self) -> List[int]:
        r"""Returns the cutoff dimensions for each mode."""
        return self.representation.cutoffs

    # @property
    # #TODO: Depends on the representation. Shape means something else.
    # def shape(self) -> List[int]:
    #     r"""Returns the shape of the state.
    #     """
    #     return self.cutoffs if self.is_pure else self.cutoffs + self.cutoffs

    @SafeProperty
    def fock_array(self) -> ComplexTensor:
        r"""Returns the Fock representation of the state."""
        return self.representation.data.array  # if unavailable will raise AttributeError from data

    @SafeProperty
    def number_means(self) -> RealVector:
        r"""Returns the mean photon number for each mode."""
        return self.representation.number_means()

    @SafeProperty
    def number_cov(self) -> RealMatrix:
        r"""Returns the complete photon number covariance matrix."""
        return self.representation.number_cov()

    @SafeProperty
    def norm(self) -> float:  # NOTE: risky: need to make sure user knows what kind of norm
        r"""Returns the norm of the state."""
        return self.representation.norm

    @SafeProperty
    def state_probability(self) -> float:
        r"""Returns the probability of the state."""
        return self.representation.probability

    def fock_probabilities(self, cutoffs: Sequence[int]) -> RealTensor:
        r"""Returns the probabilities in Fock representation.

        If the state is pure, they are the absolute value squared of the ket amplitudes.
        If the state is mixed they are the multi-dimensional diagonals of the density matrix.

        Args:
            cutoffs List[int]: the cutoff dimensions for each mode

        Returns:
            Tensor: the probabilities
        """
        # TODO: deal with the cutoff issue here
        if self.is_fock:
            return self.representation.probabilities(cutoffs)

    def primal(self, other: Union[State, Transformation]) -> State:
        r"""Returns the post-measurement state after ``other`` is projected onto ``self``.

        ``other << self`` is other projected onto ``self``.

        If ``other`` is a ``Transformation``, it returns the dual of the transformation applied to
        ``self``: ``other << self`` is like ``self >> other^dual``.

        Note that the returned state is not normalized. To normalize a state you can use
        ``mrmustard.physics.normalize``.
        """
        # TODO: touch this primal when refactor measurement

        if isinstance(other, State):
            return self._project_onto_state(other)
        try:
            return other.dual(self)
        except AttributeError as e:
            raise TypeError(
                f"Cannot apply {other.__class__.__qualname__} to {self.__class__.__qualname__}"
            ) from e

    def _project_onto_state(self, other: State) -> Union[State, float]:  # TODO: move to measurement
        r"""If states are gaussian use generaldyne measurement, else use
        the states' Fock representation."""

        # if both states are gaussian
        if self.is_wigner and other.is_wigner:
            return self._project_onto_gaussian(other)

        # either self or other is not gaussian
        return self._project_onto_fock(other)

    def _project_onto_fock(self, other: State) -> Union[State, float]:  # TODO: move to measurement
        r"""Returns the post-measurement state of the projection between two non-Gaussian
        states on the remaining modes or the probability of the result. When doing homodyne sampling,
        returns the post-measurement state or the measument outcome if no modes remain.

        Args:
            other (State): state being projected onto self

        Returns:
            State or float: returns the conditional state on the remaining modes
                or the probability.
        """
        remaining_modes = list(set(other.modes) - set(self.modes))

        out_fock = self._contract_with_other(other)
        if len(remaining_modes) > 0:
            return (
                DM(fock_array=out_fock, modes=remaining_modes)
                if other.is_mixed or self.is_mixed
                else Ket(fock_array=out_fock, modes=remaining_modes)
            )

        # return the probability (norm) of the state when there are no modes left
        return (
            fock.math.abs(out_fock) ** 2
            if other.is_pure and self.is_pure
            else fock.math.abs(out_fock)  # TODO check this
        )

    def _contract_with_other(self, other):
        other_cutoffs = [
            None if m not in self.modes else other.cutoffs[other.indices(m)] for m in other.modes
        ]
        if hasattr(self, "_preferred_projection"):
            out_fock = self._preferred_projection(other, other.indices(self.modes))
        else:
            # matching other's cutoffs
            self_cutoffs = [other.cutoffs[other.indices(m)] for m in self.modes]
            out_fock = fock.contract_states(
                stateA=other.ket(other_cutoffs) if other.is_pure else other.dm(other_cutoffs),
                stateB=self.ket(self_cutoffs) if self.is_pure else self.dm(self_cutoffs),
                a_is_dm=other.is_mixed,
                b_is_dm=self.is_mixed,
                modes=other.indices(self.modes),
                normalize=self._normalize if hasattr(self, "_normalize") else False,
            )

        return out_fock

    def _project_onto_gaussian(self, other: State) -> Union[State, float]:
        r"""Returns the result of a generaldyne measurement given that states ``self`` and
        ``other`` are gaussian.

        Args:
            other (State): gaussian state being projected onto self

        Returns:
            State or float: returns the output conditional state on the remaining modes
                or the probability.
        """
        # here `self` is the measurement device state and `other` is the incoming state
        # being projected onto the measurement state
        remaining_modes = list(set(other.modes) - set(self.modes))

        _, probability, new_cov, new_means = gaussian.general_dyne(
            other.cov,
            other.means,
            self.cov,
            self.means,
            self.modes,
        )

        if len(remaining_modes) > 0:
            return State(
                means=new_means,
                cov=new_cov,
                modes=remaining_modes,
                _norm=probability if not getattr(self, "_normalize", False) else 1.0,
            )

        return probability

    # def __iter__(self) -> Iterable[State]:
    #     """Iterates over the modes and their corresponding tensors."""
    #     return (self.get_modes(i) for i in range(self.representation.num_modes))

    def __and__(self, other: State) -> State:
        r"""Concatenates two states."""
        return self.representation.data.__and__(other)

    def __getitem__(self, item) -> State:  # NOTE should this be getting the modes instead?
        "setting the modes of a state (same API of `Transformation`)"
        if isinstance(item, int):
            item = [item]
        elif isinstance(item, Iterable):
            item = list(item)
        else:
            raise TypeError("item must be int or iterable")
        if len(item) != self.num_modes:
            raise ValueError(
                f"there are {self.num_modes} modes (item has {len(item)} elements, perhaps you're looking for .get_modes()?)"
            )
        self._modes = item  # TODO return a new state with the modes set instead of mutating
        return self

    def get_modes(self, item) -> State:
        r"""Returns the state on the given modes."""
        if isinstance(item, int):
            item = [item]
        elif isinstance(item, Iterable):
            item = list(item)
        else:
            raise TypeError("item must be int or iterable")

        if item == self._modes:
            return self

        if not set(item) & set(self._modes):
            raise ValueError(
                f"Failed to request modes {item} for state {self} on modes {self._modes}."
            )
        item_idx = [self._modes.index(m) for m in item]
        if self.is_wigner:
            cov, _, _ = gaussian.partition_cov(self.cov, item_idx)
            means, _ = gaussian.partition_means(self.means, item_idx)
            return State(cov=cov, means=means, modes=item)

        fock_partitioned = fock.trace(
            self.dm(self.cutoffs), keep=item_idx
        )  # TODO: this self.cutoffs is not correct now with the new structure
        return State(dm=fock_partitioned, modes=item)

    def __eq__(self, other) -> bool:  # pylint: disable=too-many-return-statements
        r"""Returns whether the states are equal."""
        return self.representation.data.__eq__(other)

    def __rshift__(self, other: Transformation) -> State:
        r"""Applies other (a Transformation) to self (a State), e.g., ``Coherent(x=0.1) >> Sgate(r=0.1)``."""
        if issubclass(other.__class__, State):
            raise TypeError(
                f"Cannot apply {other.__class__.__qualname__} to a state. Are you looking for the << operator?"
            )
        return other.primal(self)

    def __lshift__(self, other: State):
        r"""Implements projection onto a state or the dual transformation applied on a state.

        E.g., ``self << other`` where other is a ``State`` and ``self`` is either a ``State`` or a ``Transformation``.
        """
        return other.primal(self)

    def __add__(self, other: State):
        r"""Implements a mixture of states (only available in fock representation for the moment)."""
        return self.representation.data.__add__(other)

    def __rmul__(self, other):
        r"""Implements multiplication by a scalar from the left.

        E.g., ``0.5 * psi``.
        """
        return self.representation.data.__rmul__(other)

    def __mul__(self, other: State):
        r"""Implements multiplication of two objects."""
        return self.representation.data.__rmul__(other)

    def __truediv__(self, other):
        r"""Implements division by a scalar from the left.

        E.g. ``psi / 0.5``
        """
        return self.representation.data.__truediv__(other)

    @staticmethod
    def _format_probability(prob: Optional[float]) -> str:
        if prob is None:
            return "None"
        if prob < 0.001:
            return f"{100*prob:.3e} %"
        else:
            return f"{prob:.3%}"

    def to_Bargmann(self):
        r"""Converts the representation of the state to Bargmann Representation and returns self.

        Returns:
            State: the converted state with the target Bargmann Representation
        """
        self.representation = converter.convert(self.representation, "Bargmann")
        return self

    def to_Fock(
        self,
        max_prob: Optional[float] = None,
        max_photon: Optional[int] = None,
        cutoffs: Optional[List[int]] = None,
        shape: Optional[List[int]] = None,
    ):
        r"""Converts the representation of the state to Fock Representation and returns self.

        Args:
            max_prob (optional float): The maximum probability of the state. Defaults to settings.AUTOCUTOFF_PROBABILITY.
                (used to stop the calculation of the amplitudes early)
            max_photons (optional int): The maximum number of photons in the state, summing over all modes
                (used to stop the calculation of the amplitudes early)
            cutoffs (optional List[int]): The cutoffs of the desired Fock tensor. Defaults to autocutoffs.
            shape (optional List[int]): The shape of the desired Fock tensor. Overrides cutoffs.

        Returns:
            State: the converted state with the target Fock Representation
        """
        self.representation = converter.convert(
            self.representation,
            "Fock",
            max_prob=max_prob or settings.AUTOCUTOFF_PROBABILITY,
            max_photon=max_photon,
            cutoffs=cutoffs,
        )
        return self

    def to_WaveFunctionQ(self):
        r"""Converts the representation of the state to q-wavefunction Representation and returns self.

        Returns:
            State: the converted state with the target q-Wavefunction Representation
        """
        self.representation = converter.convert(self.representation, "WaveFunctionQ")
        return self

    def to_Wigner(self):
        r"""Converts the representation of the state to Wigner Representation and returns self.

        Returns:
            State: the converted state with the target Wigner Representation
        """
        self.representation = converter.convert(self.representation, "Wigner")
        return self

    def _repr_markdown_(self):
        r"""Prints the table to show the properties of the state."""
        purity = self.purity
        probability = self.state_probability
        num_modes = self.representation.num_modes
        bosonic_size = "1" if isinstance(self.representation, (WignerKet, WignerDM)) else "N/A"
        representation = self.representation.name
        table = (
            f"#### {self.__class__.__qualname__}\n\n"
            + "| Purity | Probability | Num modes | Bosonic size | Representation |\n"
            + "| :----: | :----: | :----: | :----: | :----: |\n"
            + f"| {purity :.2e} | "
            + self._format_probability(probability)
            + f" | {num_modes} | {bosonic_size} | {representation} |"
        )

        if self.num_modes == 1:
            graphics.mikkel_plot(math.asnumpy(self.dm(cutoffs=self.representation.data.cutoffs)))

        # TODO:
        # if settings.DEBUG:
        #     detailed_info = f"\ncov={repr(self.cov)}\n" + f"means={repr(self.means)}\n"
        #     return f"{table}\n{detailed_info}"

        return table


class Ket(State):
    def _from_Abc(self, A, b, c):
        self.representation = BargmannKet(A, b, c)

    def _from_cov_means(self, cov, means):
        # decomposes cov into SS^T and uses S internally
        symplectic = math.cholesky(cov)
        self.representation = WignerKet(symplectic, means)

    def _from_fock_array(self, fock_array):
        self.representation = FockKet(fock_array)

    def _from_wf_q_array(self, qs, wf_q_array):
        self.representation = WaveFunctionQKet(qs, wf_q_array)

    @property
    def purity(self) -> float:
        r"""Returns the purity of the state."""
        return 1.0

    @SafeProperty
    def cov(self):  # override because Ket doesn't have a covariance matrix per se
        r"""Returns the covariance matrix of the state."""
        S = self.representation.symplectic
        return math.matmul(S, math.transpose(S))

    def ket(self, cutoffs: List[int] = None) -> Optional[ComplexTensor]:
        r"""Returns the ket of the state if it is in Fock representation.

        Args:
            cutoffs List[int or None]: The cutoff dimension for each mode. If a mode cutoff is
                ``None``, it's guessed automatically.

        Returns:
            Tensor: the ket
        """
        if isinstance(self.representation, FockKet):
            if cutoffs is None:
                return self.representation.data.array
            else:  # TODO: cutoffs could be smaller too!
                return fock.pad_array_with_cutoffs(self.representation.data.array, cutoffs)
        else:
            raise AttributeError(
                "Use .to_Fock() to transform the state to Fock representation first."
            )

    def dm(self, cutoffs: Optional[List[int]] = None) -> ComplexTensor:
        ket = self.ket(cutoffs)
        return math.tensordot(ket, math.conj(ket), [[], []])


class DM(State):
    def _from_Abc(self, A, b, c):
        self.representation = BargmannDM(A, b, c)

    def _from_cov_means(self, cov, means):
        self.representation = WignerDM(cov, means, check_purity=True)

    def _from_fock_array(self, fock_array):
        self.representation = FockDM(fock_array)

    def _from_wf_q_array(self, qs, wf_q_array):
        self.representation = WaveFunctionQDM(qs, wf_q_array)

    def ket(self, cutoffs: Optional[List[int]] = None) -> Optional[ComplexTensor]:
        pass  # compute only if state is pure

    def dm(self, cutoffs: Optional[List[int]] = None) -> ComplexTensor:
        r"""Returns the density matrix of the state in Fock representation.

        Args:
            cutoffs (optional List[int]): The cutoff dimensions for each mode. If a mode cutoff is ``None``,
                it's automatically computed.

        Returns:
            Tensor: the density matrix
        """

        if isinstance(self.representation, FockDM):
            if cutoffs is None:
                return self.representation.data.array
            return fock.pad_array_with_cutoffs(
                self.representation.data.array, cutoffs
            )  # TODO: use shape (this is a dm)
        else:
            raise AttributeError(
                "Use .to_Fock to transform the state to Fock representation first."
            )