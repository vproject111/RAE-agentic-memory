"""Unit tests for Semantic Resonance Calculator."""

from rae_core.math.semantic_resonance import SemanticResonance


def test_calculate_empty_query():
    sr = SemanticResonance()
    assert sr.calculate("") == 0.5


def test_calculate_specific_query_id():
    sr = SemanticResonance()
    # Query with many special characters (ID-like)
    query = "ID-1234-5678-ABCD-EFGH"
    # special_chars: -, -, -, - (4)
    # length: 22
    # special_density: 4/22 = 0.18 > 0.1
    assert sr.calculate(query) == 0.1


def test_calculate_specific_query_code():
    sr = SemanticResonance()
    query = "def my_func(a, b): return a + b"
    # special_chars: (, ,, ), :, +, (5)
    # length: 31
    # special_density: 5/31 = 0.16 > 0.1
    assert sr.calculate(query) == 0.1


def test_calculate_abstract_query():
    sr = SemanticResonance()
    query = "What is the meaning of life and the nature of consciousness?"
    score = sr.calculate(query)
    assert 0.0 <= score <= 1.0
    # Should be relatively high but less than 1.0 due to formula
    assert score > 0.1


def test_calculate_token_diversity():
    sr = SemanticResonance()
    query = "word word word word"
    score_low_diversity = sr.calculate(query)

    query_high = "one two three four"
    score_high_diversity = sr.calculate(query_high)

    assert score_high_diversity > score_low_diversity


def test_shannon_entropy():
    sr = SemanticResonance()
    # All same characters
    assert sr._shannon_entropy("aaaaa") == 0.0
    # Different characters
    assert sr._shannon_entropy("abcd") > 0.0


def test_calculate_near_boundary_special_density():
    sr = SemanticResonance()
    # query length 10, 1 special char -> 0.1 density.
    # Should not trigger the 0.1 return yet if it's <= 0.1
    query = "abcde fgh!"
    score = sr.calculate(query)
    assert score != 0.1

    # query length 10, 2 special chars -> 0.2 density.
    query = "abcd! fgh?"
    score = sr.calculate(query)
    assert score == 0.1
