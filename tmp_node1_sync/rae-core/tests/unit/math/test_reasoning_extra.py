from rae_core.math.reasoning import ReasoningController, ReasoningPath


def test_reasoning_path_similarity_to_empty():
    p1 = ReasoningPath(steps=["test"])
    p2 = ReasoningPath(steps=[])

    assert p1.similarity_to(p2) == 0.0
    assert p2.similarity_to(p1) == 0.0


def test_reasoning_controller_contradicts_memories_no_memories():
    controller = ReasoningController()
    path = ReasoningPath(steps=["test"])

    # Line 342
    assert controller._contradicts_memories(path, []) is False
