import numpy as np
import tensorflow as tf
from mrmustard.backends import BackendInterface, Autocast
from thewalrus._hermite_multidimensional import hermite_multidimensional_numba, grad_hermite_multidimensional_numba
from mrmustard._typing import *

#  NOTE: the reason why we have a class with methods and not a namespace with functions
#  is that we want to enforce the interface, in order to ensure compatibility
#  of new backends with the rest of the codebase.


class Backend(BackendInterface):

    float64 = tf.float64
    float32 = tf.float32
    complex64 = tf.complex64
    complex128 = tf.complex128

    # ~~~~~~~~~
    # Basic ops
    # ~~~~~~~~~

    def atleast_1d(self, array: tf.Tensor, dtype=None) -> tf.Tensor:
        return self.cast(tf.reshape(array, [-1]), dtype)

    def astensor(self, array: Union[np.ndarray, tf.Tensor], dtype=None) -> tf.Tensor:
        return tf.convert_to_tensor(array, dtype=dtype)
    
    def conj(self, array: tf.Tensor) -> tf.Tensor:
        return tf.math.conj(array)

    def real(self, array: tf.Tensor) -> tf.Tensor:
        return tf.math.real(array)

    def imag(self, array: tf.Tensor) -> tf.Tensor:
        return tf.math.imag(array)

    def cos(self, array: tf.Tensor) -> tf.Tensor:
        return tf.math.cos(array)

    def cosh(self, array: tf.Tensor) -> tf.Tensor:
        return tf.math.cosh(array)

    def sinh(self, array: tf.Tensor) -> tf.Tensor:
        return tf.math.sinh(array)

    def sin(self, array: tf.Tensor) -> tf.Tensor:
        return tf.math.sin(array)

    def exp(self, array: tf.Tensor) -> tf.Tensor:
        return tf.math.exp(array)

    def sqrt(self, x: tf.Tensor, dtype=None) -> tf.Tensor:
        return self.cast(tf.sqrt(x), dtype)

    def lgamma(self, x: tf.Tensor) -> tf.Tensor:
        return tf.math.lgamma(x)

    def log(self, x: tf.Tensor) -> tf.Tensor:
        return tf.math.log(x)

    def cast(self, x: tf.Tensor, dtype=None) -> tf.Tensor:
        if dtype is None:
            return x
        return tf.cast(x, dtype)

    @Autocast()
    def maximum(self, a: tf.Tensor, b: tf.Tensor) -> tf.Tensor:
        return tf.maximum(a, b)

    @Autocast()
    def minimum(self, a: tf.Tensor, b: tf.Tensor) -> tf.Tensor:
        return tf.minimum(a, b)

    def abs(self, array: tf.Tensor) -> tf.Tensor:
        return tf.abs(array)

    def expm(self, matrix: tf.Tensor) -> tf.Tensor:
        return tf.linalg.expm(matrix)

    def norm(self, array: tf.Tensor) -> tf.Tensor:
        'Note that the norm preserves the type of array'
        return tf.linalg.norm(array)

    @Autocast()
    def matmul(self, a: tf.Tensor, b: tf.Tensor, transpose_a=False, transpose_b=False, adjoint_a=False, adjoint_b=False)  -> tf.Tensor:
        return tf.linalg.matmul(a, b, transpose_a, transpose_b, adjoint_a, adjoint_b)

    @Autocast()
    def matvec(self, a: tf.Tensor, b: tf.Tensor, transpose_a=False, adjoint_a=False) -> tf.Tensor:
        return tf.linalg.matvec(a, b, transpose_a, adjoint_a)

    @Autocast()
    def tensordot(self, a: tf.Tensor, b: tf.Tensor, axes: List[int]) -> tf.Tensor:
        return tf.tensordot(a, b, axes)

    def einsum(self, string: str, *tensors) -> tf.Tensor: 
        return tf.einsum(string, *tensors)

    def inv(self, a: tf.Tensor) -> tf.Tensor:
        return tf.linalg.inv(a)

    def pinv(self, array: tf.Tensor) -> tf.Tensor:
        return tf.linalg.pinv(array)

    def det(self, a: tf.Tensor) -> tf.Tensor:
        return tf.linalg.det(a)

    def tile(self, array: tf.Tensor, repeats: Sequence[int]) -> tf.Tensor:
        return tf.tile(array, repeats)

    def diag(self, array: tf.Tensor, k: int = 0) -> tf.Tensor:
        return tf.linalg.diag(array, k=k)

    def diag_part(self, array: tf.Tensor) -> tf.Tensor:
        return tf.linalg.diag_part(array)

    def pad(self, array: tf.Tensor, paddings: Sequence[Tuple[int, int]], mode='CONSTANT', constant_values=0) -> tf.Tensor:
        return tf.pad(array, paddings, mode, constant_values)

    @Autocast()
    def convolution(self, array: tf.Tensor, filters: tf.Tensor, strides: Optional[List[int]] = None, padding='VALID', data_format='NWC', dilations: Optional[List[int]] = None) -> tf.Tensor:
        return tf.nn.convolution(array, filters, strides, padding, data_format, dilations)

    def transpose(self, a: tf.Tensor, perm: List[int] = None) -> tf.Tensor:
        if a is None:
            return None  # TODO: remove and address None inputs where tranpose is used
        return tf.transpose(a, perm)

    def reshape(self, array: tf.Tensor, shape: Sequence[int]) -> tf.Tensor:
        return tf.reshape(array, shape)

    def sum(self, array: tf.Tensor, axes: Sequence[int]=None):
        return tf.reduce_sum(array, axes)

    def arange(self, start: int, limit: int = None, delta: int = 1, dtype=tf.float64) -> tf.Tensor:
        return tf.range(start, limit, delta, dtype=dtype)

    @Autocast()
    def outer(self, array1: tf.Tensor, array2: tf.Tensor) -> tf.Tensor:
        return tf.tensordot(array1, array2, [[], []])

    def eye(self, size: int, dtype=tf.float64) -> tf.Tensor:
        return tf.eye(size, dtype=dtype)

    def zeros(self, shape: Sequence[int], dtype=tf.float64) -> tf.Tensor:
        return tf.zeros(shape, dtype=dtype)

    def zeros_like(self, array: tf.Tensor) -> tf.Tensor:
        return tf.zeros_like(array)

    def ones(self, shape: Sequence[int], dtype=tf.float64) -> tf.Tensor:
        return tf.ones(shape, dtype=dtype)

    def ones_like(self, array: tf.Tensor) -> tf.Tensor:
        return tf.ones_like(array)

    def gather(self, array: tf.Tensor, indices: tf.Tensor, axis: int = None) -> tf.Tensor:
        return tf.gather(array, indices, axis=axis)

    def trace(self, array: tf.Tensor, dtype=None) -> tf.Tensor:
        return self.cast(tf.linalg.trace(array), dtype)

    def concat(self, values: Sequence[tf.Tensor], axis: int) -> tf.Tensor:
        return tf.concat(values, axis)

    def update_tensor(self, tensor: tf.Tensor, indices: tf.Tensor, values: tf.Tensor):
        return tf.tensor_scatter_nd_update(tensor, indices, values)

    def update_add_tensor(self, tensor: tf.Tensor, indices: tf.Tensor, values: tf.Tensor):
        return tf.tensor_scatter_nd_add(tensor, indices, values)

    def constraint_func(self, bounds: Tuple[Optional[float], Optional[float]]) -> Optional[Callable]:
        bounds = (-np.inf if bounds[0] is None else bounds[0], np.inf if bounds[1] is None else bounds[1])
        if not bounds == (-np.inf, np.inf):
            constraint: Optional[Callable] = lambda x: tf.clip_by_value(x, bounds[0], bounds[1])
        else:
            constraint = None
        return constraint

    def new_variable(self, value, bounds: Tuple[Optional[float], Optional[float]], name: str, dtype=tf.float64):
        return tf.Variable(value, name=name, dtype=dtype, constraint=self.constraint_func(bounds))

    def new_constant(self, value, name: str, dtype=tf.float64):
        return tf.constant(value, dtype=dtype, name=name)

    def asnumpy(self, tensor: tf.Tensor) -> Tensor:
        return tensor.numpy()

    def hash_tensor(self, tensor: tf.Tensor) -> str:
        try:
            REF = tensor.ref()
        except AttributeError:
            raise TypeError(f'Cannot hash tensor')
        return hash(REF)

    @tf.custom_gradient
    def hermite_renormalized(self, A: tf.Tensor, B: tf.Tensor, C: tf.Tensor, shape: Tuple[int]) -> tf.Tensor:  # TODO this is not ready
        r"""
        Renormalized multidimensional Hermite polynomial given by the "exponential" Taylor series
        of exp(Ax^2 + Bx + C) at zero, where the series has `sqrt(n!)` at the denominator rather than `n!`.

        Args:
            A: The A matrix.
            B: The B vector.
            C: The C scalar.
            shape: The shape of the final tensor.
        Returns:
            The renormalized Hermite polynomial of given shape.
        """
        poly = self.conj(hermite_multidimensional_numba(-A, tuple(shape), B, C))

        def grad(dLdpoly):
            dpoly_dC, dpoly_dA, dpoly_dB = grad_hermite_multidimensional_numba(poly, -A, shape, B, C)
            ax = tuple(range(dLdpoly.ndim))
            dLdA = self.sum(dLdpoly[..., None, None] * self.conj(dpoly_dA), axis=ax)
            dLdB = self.sum(dLdpoly[..., None] * self.conj(dpoly_dB), axis=ax)
            dLdC = self.sum(dLdpoly * self.conj(dpoly_dC), axis=ax)
            return dLdA, dLdB, dLdC

        return poly, grad

    def DefaultEuclideanOptimizer(self) -> tf.keras.optimizers.Optimizer:
        r"""
        Default optimizer for the Euclidean parameters.
        """
        return tf.keras.optimizers.Adam(learning_rate=0.001)

    def loss_and_gradients(self, cost_fn: Callable, parameters: Dict[str, List[Trainable]]) -> Tuple[tf.Tensor, Dict[str, List[tf.Tensor]]]:
        r"""
        Computes the loss and gradients of the given cost function.

        Arguments:
            cost_fn (Callable with no args): The cost function.
            parameters (Dict): The parameters to optimize in three kinds:
                symplectic, orthogonal and euclidean.
        
        Returns:
            The loss and the gradients.
        """
        with tf.GradientTape() as tape:
            loss = cost_fn()
        gradients = tape.gradient(loss, list(parameters.values()))
        return loss, dict(zip(parameters.keys(), gradients))