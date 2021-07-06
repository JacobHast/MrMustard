from typing import List, Tuple, Optional, Union
from mrmustard.core.baseclasses.parametrized import Parametrized
from mrmustard.core.baseclasses import Gate


class Dgate(Parametrized, Gate):
    r"""
    Displacement gate. If len(modes) > 1 the gate is applied in parallel to all of the modes provided.
    If a parameter is a single float, the parallel instances of the gate share that parameter.
    To apply mode-specific values use a list of floats.
    One can optionally set bounds for each parameter, which the optimizer will respect.

    Arguments:
        modes (List[int]): the list of modes this gate is applied to
        x (float or List[float]): the list of displacements along the x axis
        x_bounds (float, float): bounds for the displacement along the x axis
        x_trainable (bool): whether x is a trainable variable
        y (float or List[float]): the list of displacements along the y axis
        y_bounds (float, float): bounds for the displacement along the y axis
        y_trainable bool: whether y is a trainable variable
    """

    def __init__(
        self,
        modes: List[int],
        x: Union[Optional[float], Optional[List[float]]] = None,
        x_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        x_trainable: bool = True,
        y: Union[Optional[float], Optional[List[float]]] = None,
        y_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        y_trainable: bool = True,
    ):
        super().__init__(modes=modes, x=x, x_bounds=x_bounds, x_trainable=x_trainable, y=y, y_bounds=y_bounds, y_trainable=y_trainable)
        self.mixing = False

    def displacement_vector(self, hbar: float):
        return self._symplectic_backend.displacement(self.x, self.y, hbar=hbar)


class Sgate(Parametrized, Gate):
    r"""
    Squeezing gate. If len(modes) > 1 the gate is applied in parallel to all of the modes provided.
    If a parameter is a single float, the parallel instances of the gate share that parameter.
    To apply mode-specific values use a list of floats.
    One can optionally set bounds for each parameter, which the optimizer will respect.

    Arguments:
        modes (List[int]): the list of modes this gate is applied to
        r (float or List[float]): the list of squeezing magnitudes
        r_bounds (float, float): bounds for the squeezing magnitudes
        r_trainable (bool): whether r is a trainable variable
        phi (float or List[float]): the list of squeezing angles
        phi_bounds (float, float): bounds for the squeezing angles
        phi_trainable bool: whether phi is a trainable variable
    """

    def __init__(
        self,
        modes: List[int],
        r: Union[Optional[float], Optional[List[float]]] = None,
        r_bounds: Tuple[Optional[float], Optional[float]] = (0.0, None),
        r_trainable: bool = True,
        phi: Union[Optional[float], Optional[List[float]]] = None,
        phi_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        phi_trainable: bool = True,
    ):
        super().__init__(
            modes=modes, r=r, r_bounds=r_bounds, r_trainable=r_trainable, phi=phi, phi_bounds=phi_bounds, phi_trainable=phi_trainable
        )
        self.mixing = False

    def symplectic_matrix(self, hbar: float):
        return self._symplectic_backend.squeezing_symplectic(self.r, self.phi)


class Rgate(Parametrized, Gate):
    r"""
    Rotation gate. If len(modes) > 1 the gate is applied in parallel to all of the modes provided.
    If a parameter is a single float, the parallel instances of the gate share that parameter.
    To apply mode-specific values use a list of floats.
    One can optionally set bounds for each parameter, which the optimizer will respect.

    Arguments:
        modes (List[int]): the list of modes this gate is applied to
        angle (float or List[float]): the list of rotation angles
        angle_bounds (float, float): bounds for the rotation angles
        angle_trainable bool: whether angle is a trainable variable
    """

    def __init__(
        self,
        modes: List[int],
        angle: Union[Optional[float], Optional[List[float]]] = None,
        angle_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        angle_trainable: bool = True,
    ):
        super().__init__(modes=modes, angle=angle, angle_bounds=angle_bounds, angle_trainable=angle_trainable)
        self.mixing = False

    def symplectic_matrix(self, hbar: float):
        return self._symplectic_backend.rotation_symplectic(self.angle)


class Ggate(Parametrized, Gate):
    r"""
    General Gaussian gate. If len(modes) == N the gate represents an N-mode Gaussian unitary transformation.
    If a symplectic matrix is not provided, one will be picked at random with effective squeezings between 0 and 1.

    Arguments:
        modes (List[int]): the list of modes this gate is applied to
        symplectic (2d array): a valid symplectic matrix. For N modes it must have shape `(2N,2N)`
        symplectic_trainable (bool): whether symplectic is a trainable variable
        displacement (1d array): a displacement vector. For N modes it must have shape `(2N,)`
        displacement_trainable (bool): whether displacement is a trainable variable
    """

    def __init__(
        self,
        modes: List[int],
        symplectic: Optional = None,
        symplectic_trainable: bool = True,
        displacement: Optional = None,
        displacement_trainable: bool = True,
    ):
        if symplectic is None:
            symplectic = self._math_backend.new_symplectic_parameter(num_modes=len(modes))
        if displacement is None:
            displacement = self._math_backend.zeros(len(modes) * 2)
        super().__init__(
            modes=modes,
            symplectic=symplectic,
            symplectic_bounds=(None, None),
            symplectic_trainable=symplectic_trainable,
            displacement=displacement,
            displacement_bounds=(None, None),
            displacement_trainable=displacement_trainable,
        )
        self.mixing = False

    def symplectic_matrix(self, hbar: float = 2.0):
        return self.symplectic

    def displacement_vector(self, hbar: float = 2.0):
        return self.displacement

    @property
    def symplectic_parameters(self) -> List:
        return [mat for mat in self._trainable_parameters if len(mat.shape) == 2]

    @property
    def euclidean_parameters(self) -> List:
        return [vec for vec in self._trainable_parameters if len(vec.shape) == 1]


class BSgate(Parametrized, Gate):
    r"""
    Beam splitter gate. It applies to a single pair of modes.
    One can optionally set bounds for each parameter, which the optimizer will respect.

    Arguments:
        modes (List[int]): the pair of modes to which the beamsplitter is applied to. Must be of length 2.
        theta (float): the transmissivity angle
        theta_bounds (float, float): bounds for the transmissivity angle
        theta_trainable (bool): whether theta is a trainable variable
        phi (float): the phase angle
        phi_bounds (float, float): bounds for the phase angle
        phi_trainable bool: whether phi is a trainable variable
    """

    def __init__(
        self,
        modes: List[int],
        theta: Optional[float] = None,
        theta_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        theta_trainable: bool = True,
        phi: Optional[float] = None,
        phi_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        phi_trainable: bool = True,
    ):
        if len(modes) > 2:
            raise ValueError("Beam splitter works on 2 modes. Perhaps you are looking for Interferometer.")
        super().__init__(
            modes=modes,
            theta=theta,
            theta_bounds=theta_bounds,
            theta_trainable=theta_trainable,
            phi=phi,
            phi_bounds=phi_bounds,
            phi_trainable=phi_trainable,
        )
        self.mixing = False

    def symplectic_matrix(self, hbar: float):
        return self._symplectic_backend.beam_splitter_symplectic(self.theta, self.phi)


class MZgate(Parametrized, Gate):
    r"""
    Mach-Zehnder gate. It supports two conventions:
        1. if `internal=True`, both phases act iside the interferometer: `phi_a` on the upper arm, `phi_b` on the lower arm;
        2. if `internal = False`, both phases act on the upper arm: `phi_a` before the first BS, `phi_b` after the first BS.
    One can optionally set bounds for each parameter, which the optimizer will respect.

    Arguments:
        modes (List[int]): the pair of modes to which the beamsplitter is applied to. Must be of length 2.
        phi_a (float): the phase in the upper arm of the MZ interferometer
        phi_a_bounds (float, float): bounds for phi_a
        phi_a_trainable (bool): whether phi_a is a trainable variable
        phi_b (float): the phase in the lower arm or external of the MZ interferometer
        phi_b_bounds (float, float): bounds for phi_b
        phi_b_trainable (bool): whether phi_b is a trainable variable
        internal (bool): whether phases are both in the internal arms (default is False)
    """

    def __init__(
        self,
        modes: List[int],
        phi_a: Optional[float] = None,
        phi_a_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        phi_a_trainable: bool = True,
        phi_b: Optional[float] = None,
        phi_b_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        phi_b_trainable: bool = True,
        internal: bool = False,
    ):
        if len(modes) > 2:
            raise ValueError("The Mach-Zehnder gate works on 2 modes. Perhaps you are looking for Interferometer.")
        super().__init__(
            modes=modes,
            phi_a=phi_a,
            phi_a_bounds=phi_a_bounds,
            phi_a_trainable=phi_a_trainable,
            phi_b=phi_b,
            phi_b_bounds=phi_b_bounds,
            phi_b_trainable=phi_b_trainable,
            internal=internal,
        )
        self.mixing = False

    def symplectic_matrix(self, hbar: float):
        return self._symplectic_backend.mz_symplectic(self.phi_a, self.phi_b, internal=self._internal)


class S2gate(Parametrized, Gate):
    r"""
    Two-mode squeezing gate. It applies to a single pair of modes.
    One can optionally set bounds for each parameter, which the optimizer will respect.

    Arguments:
        modes (List[int]): the list of modes the two-mode squeezing is applied to. Must be of length 2.
        r (float): the squeezing magnitude
        r_bounds (float, float): bounds for the squeezing magnitude
        r_trainable (bool): whether r is a trainable variable
        phi (float): the squeezing angle
        phi_bounds (float, float): bounds for the squeezing angle
        phi_trainable bool: whether phi is a trainable variable
    """

    def __init__(
        self,
        modes: List[int],
        r: Optional[float] = None,
        r_bounds: Tuple[Optional[float], Optional[float]] = (0.0, None),
        r_trainable: bool = True,
        phi: Optional[float] = None,
        phi_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        phi_trainable: bool = True,
    ):
        super().__init__(
            modes=modes, r=r, r_bounds=r_bounds, r_trainable=r_trainable, phi=phi, phi_bounds=phi_bounds, phi_trainable=phi_trainable
        )
        self.mixing = False

    def symplectic_matrix(self, hbar: float):
        return self._symplectic_backend.two_mode_squeezing_symplectic(self.r, self.phi)


class LossChannel(Parametrized, Gate):
    r"""
    The lossy bosonic channel. If len(modes) > 1 the gate is applied in parallel to all of the modes provided.
    If `transmissivity` is a single float, the parallel instances of the gate share that parameter.
    To apply mode-specific values use a list of floats.
    One can optionally set bounds for `transmissivity`, which the optimizer will respect.

    Arguments:
        modes (List[int]): the list of modes the loss is applied to
        transmissivity (float or List[float]): the list of transmissivities
        transmissivity_bounds (float, float): bounds for the transmissivity
        transmissivity_trainable (bool): whether transmissivity is a trainable variable
    """

    def __init__(
        self,
        modes: List[int],
        transmissivity: Union[Optional[float], Optional[List[float]]] = 1.0,
        transmissivity_bounds: Tuple[Optional[float], Optional[float]] = (0.0, 1.0),
        transmissivity_trainable: bool = False,
    ):
        super().__init__(
            modes=modes,
            transmissivity=transmissivity,
            transmissivity_bounds=transmissivity_bounds,
            transmissivity_trainable=transmissivity_trainable,
        )
        self.mixing = True

    def symplectic_matrix(self, hbar: float):
        return self._symplectic_backend.loss_X(self.transmissivity)

    def noise_matrix(self, hbar: float):
        return self._symplectic_backend.loss_Y(self.transmissivity, hbar=hbar)
