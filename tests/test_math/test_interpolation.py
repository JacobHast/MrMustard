import hypothesis.strategies as st
import numpy as np
from hypothesis import given
from hypothesis.extra.numpy import arrays
from scipy.interpolate import interp1d

from mrmustard.math.interpolation import ComplexFunction1D

float_ = st.floats(min_value=-10.0, max_value=10.0, allow_infinity=False, allow_nan=False)
complex_ = st.complex_numbers(
    min_magnitude=0.0, max_magnitude=10.0, allow_infinity=False, allow_nan=False
)
complex_nonzero = st.complex_numbers(
    min_magnitude=1e-6, max_magnitude=10.0, allow_infinity=False, allow_nan=False
)


@st.composite
def real_vector(draw, length):
    r"""Return a vector of length `length` with unique elements."""
    return draw(arrays(float, (length,), elements=float_, unique=True))


@st.composite
def complex_vector(draw, length):
    r"""Return a vector of length `length`."""
    return draw(arrays(complex, (length,), elements=complex_, unique=True))


@st.composite
def complex_vector_nonzero(draw, length):
    r"""Return a vector of length `length` with nonzero elements."""
    return draw(arrays(complex, (length,), elements=complex_nonzero, unique=True))


N = 3


@given(real_vector(N), complex_vector(N))
def test_creation_of_function(x, y):
    f = ComplexFunction1D(x, y)

    assert isinstance(f.interp_real, interp1d)
    assert isinstance(f.interp_imag, interp1d)


@given(real_vector(N), complex_vector(N))
def test_evaluation_of_function(x, y):
    f = ComplexFunction1D(x, y)

    assert f(x[0]) == y[0]
    assert f(x[1]) == y[1]
    assert f(x[2]) == y[2]


@given(real_vector(N), complex_vector(N), complex_vector(N))
def test_addition_of_functions(x, y1, y2):
    f1 = ComplexFunction1D(x, y1)
    f2 = ComplexFunction1D(x, y2)

    assert (-f1 + f2)(x[0]) == -f1(x[0]) + f2(x[0])
    assert (f1 + f2)(x[1]) == f1(x[1]) + f2(x[1])
    assert (f1 + f2)(x[2]) == f1(x[2]) + f2(x[2])


@given(real_vector(N), complex_vector(N), complex_vector(N))
def test_multiplication_of_functions(x, y1, y2):
    f1 = ComplexFunction1D(x, y1)
    f2 = ComplexFunction1D(x, y2)

    f3 = f1 * f2

    assert f3(x[0]) == y1[0] * y2[0]
    assert f3(x[1]) == y1[1] * y2[1]
    assert f3(x[2]) == y1[2] * y2[2]


@given(real_vector(N), complex_vector(N))
def test_scalar_operations(x, y):
    f = ComplexFunction1D(x, y)

    assert (f + 1)(x[0]) == f(x[0]) + 1
    assert (f + 1)(x[1]) == f(x[1]) + 1
    assert (f + 1)(x[2]) == f(x[2]) + 1

    assert (f * 2)(x[0]) == f(x[0]) * 2
    assert (f * 2)(x[1]) == f(x[1]) * 2
    assert (f * 2)(x[2]) == f(x[2]) * 2


@given(real_vector(N), complex_vector(N), complex_vector(N))
def test_interpolation(x, y1, y2):
    f1 = ComplexFunction1D(x, y1)
    f2 = ComplexFunction1D(x, y2)
    domain = ComplexFunction1D._intersect_ranges(f1, f2)
    f3 = f1 + f2
    x = np.linspace(domain[0], domain[-1], 100)
    for x in domain:
        assert f3(x) == f1(x) + f2(x)
    f4 = f1 * f2
    for x in domain:
        assert f4(x) == f1(x) * f2(x)


@given(real_vector(N), complex_vector(N), complex_vector(N))
def test_subtraction(x, y1, y2):
    f1 = ComplexFunction1D(x, y1)
    f2 = ComplexFunction1D(x, y2)
    f3 = f1 - f2
    for x in f1.interp_real.x:
        assert f3(x) == f1(x) - f2(x)


@given(real_vector(N), complex_vector_nonzero(N), complex_vector_nonzero(N))
def test_division(x, y1, y2):
    f1 = ComplexFunction1D(x, y1)
    f2 = ComplexFunction1D(x, y2)
    f3 = f1 / f2
    for x in f1.interp_real.x:
        assert f3(x) == f1(x) / f2(x)


@given(real_vector(N), complex_vector(N))
def test_negation(x, y):
    f = ComplexFunction1D(x, y)
    f2 = -f
    for x in f.interp_real.x:
        assert f2(x) == -f(x)
