from rae_core.math.structure import DecayConfig, ScoringWeights, cosine_similarity


def test_structure_to_dict():
    s = ScoringWeights()
    assert isinstance(s.to_dict(), dict)

    d = DecayConfig()
    assert isinstance(d.to_dict(), dict)


def test_cosine_similarity_extra():
    # Empty vectors
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0], []) == 0.0

    # Mismatch length
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    # Zero norm
    assert cosine_similarity([0.0], [0.0]) == 0.0
    assert cosine_similarity([1.0], [0.0]) == 0.0

    # Success
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
