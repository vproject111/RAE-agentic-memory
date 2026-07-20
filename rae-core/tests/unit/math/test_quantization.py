import math

import pytest

from rae_core.math.quantization import (
    SCALE_FACTOR,
    cosine_similarity_fixed,
    dequantize_vector,
    dot_product_fixed,
    quantize_vector,
)


def test_quantize_vector():
    # Empty
    assert quantize_vector([]) == []

    # Normal
    vec = [0.1, 0.5, -0.2]
    expected = [int(round(v * SCALE_FACTOR)) for v in vec]
    assert quantize_vector(vec) == expected

    # 0.0
    assert quantize_vector([0.0]) == [0]

    # Error: NaN
    with pytest.raises(ValueError, match="Non-finite value"):
        quantize_vector([float("nan")])

    # Error: Inf
    with pytest.raises(ValueError, match="Non-finite value"):
        quantize_vector([float("inf")])


def test_dequantize_vector():
    # Empty
    assert dequantize_vector([]) == []

    # Normal
    vec = [6554, 32768, -13107]
    expected = [v / SCALE_FACTOR for v in vec]
    assert dequantize_vector(vec) == expected

    # 0
    assert dequantize_vector([0]) == [0.0]


def test_dot_product_fixed():
    # Normal
    a = [1000, 2000]
    b = [3000, 4000]
    # 1000*3000 + 2000*4000 = 3,000,000 + 8,000,000 = 11,000,000
    assert dot_product_fixed(a, b) == 11000000

    # Empty
    assert dot_product_fixed([], []) == 0

    # Mismatch
    with pytest.raises(ValueError, match="Vector dimension mismatch"):
        dot_product_fixed([1], [1, 2])


def test_cosine_similarity_fixed():
    # Orthogonal
    a = [100, 0]
    b = [0, 100]
    assert cosine_similarity_fixed(a, b) == 0.0

    # Same
    a = [100, 100]
    assert math.isclose(cosine_similarity_fixed(a, a), 1.0)

    # Opposite
    a = [100, 100]
    b = [-100, -100]
    assert math.isclose(cosine_similarity_fixed(a, b), -1.0)

    # Zero vector
    assert cosine_similarity_fixed([0, 0], [100, 100]) == 0.0
    assert cosine_similarity_fixed([100, 100], [0, 0]) == 0.0
    assert cosine_similarity_fixed([0, 0], [0, 0]) == 0.0

    # General
    a = [3, 4]  # norm 5
    b = [6, 8]  # norm 10
    # dot = 3*6 + 4*8 = 18 + 32 = 50
    # cos = 50 / (5 * 10) = 50 / 50 = 1.0
    assert math.isclose(cosine_similarity_fixed(a, b), 1.0)
