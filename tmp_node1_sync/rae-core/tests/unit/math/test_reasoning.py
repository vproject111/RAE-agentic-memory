"""Unit tests for ReasoningController."""

from uuid import uuid4

from rae_core.math.reasoning import ReasoningController, ReasoningPath


class TestReasoningPath:
    def test_add_step(self):
        path = ReasoningPath()
        node_id = str(uuid4())
        path.add_step(node_id, "Step 1", uncertainty_delta=-0.1, tokens=100)

        assert path.depth == 1
        assert path.nodes == [node_id]
        assert path.steps == ["Step 1"]
        assert path.uncertainty == 0.9
        assert path.tokens_used == 100

    def test_aligns_with(self):
        path = ReasoningPath()
        path.add_step(str(uuid4()), "User likes Python")

        assert path.aligns_with({"content": "Python"}) is True
        assert path.aligns_with({"content": "Java"}) is False
        assert path.aligns_with({}) is False

    def test_count_unverified_assumptions(self):
        path = ReasoningPath()
        path.add_step(str(uuid4()), "User lives in Warsaw")
        path.add_step(str(uuid4()), "User likes cats")

        verified = {"Warsaw"}
        assert path.count_unverified_assumptions(verified) == 1  # cats unverified

    def test_similarity_to(self):
        path1 = ReasoningPath(steps=["A", "B", "C"])
        path2 = ReasoningPath(steps=["B", "C", "D"])

        sim = path1.similarity_to(path2)
        assert 0.4 < sim < 0.6  # Intersect {B,C}, Union {A,B,C,D} -> 2/4 = 0.5


class TestReasoningController:
    def test_should_continue_reasoning(self):
        ctrl = ReasoningController(
            max_depth=5, uncertainty_threshold=0.5, token_budget_per_step=1000
        )

        # OK
        assert (
            ctrl.should_continue_reasoning(
                current_depth=2, uncertainty=0.8, tokens_used=500
            )
            is True
        )

        # Max depth
        assert (
            ctrl.should_continue_reasoning(
                current_depth=5, uncertainty=0.8, tokens_used=500
            )
            is False
        )

        # Uncertainty
        assert (
            ctrl.should_continue_reasoning(
                current_depth=2, uncertainty=0.4, tokens_used=500
            )
            is False
        )

        # Budget
        assert (
            ctrl.should_continue_reasoning(
                current_depth=2, uncertainty=0.8, tokens_used=1500
            )
            is False
        )

    def test_prune_contradictory_paths(self):
        ctrl = ReasoningController(max_unverified_assumptions=1)

        p_ok = ReasoningPath(steps=["Verified step"])
        p_bad_unverified = ReasoningPath(steps=["Step X", "Step Y"])  # 2 unverified
        p_bad_contradictory = ReasoningPath(steps=["Step Z"], contradictions=["Error"])

        paths = [p_ok, p_bad_unverified, p_bad_contradictory]
        verified = {"Verified"}

        pruned = ctrl.prune_contradictory_paths(paths, verified_facts=verified)
        assert len(pruned) == 1
        assert pruned[0] == p_ok
        assert ctrl.stats["paths_pruned_unverified"] == 1
        assert ctrl.stats["paths_pruned_contradictory"] == 1

    def test_prune_similar_to_known_false(self):
        ctrl = ReasoningController(known_false_similarity_threshold=0.6)
        false_path = ReasoningPath(steps=["Common", "Mistake"])
        ctrl.mark_path_as_false(false_path)

        p_similar = ReasoningPath(steps=["Common", "Mistake", "Extra"])
        p_different = ReasoningPath(steps=["Distinct", "Path"])

        pruned = ctrl.prune_contradictory_paths([p_similar, p_different])
        assert len(pruned) == 1
        assert pruned[0] == p_different
        assert ctrl.stats["paths_pruned_similar_to_false"] == 1

    def test_stats_management(self):
        ctrl = ReasoningController()
        ctrl.should_continue_reasoning(1, 0.9, 10)
        assert ctrl.get_stats()["paths_evaluated"] == 1

        ctrl.reset_stats()
        assert ctrl.get_stats()["paths_evaluated"] == 0

    def test_clear_known_false_paths(self):
        ctrl = ReasoningController()
        ctrl.mark_path_as_false(ReasoningPath(steps=["X"]))
        assert len(ctrl.known_false_paths) == 1

        ctrl.clear_known_false_paths()
        assert len(ctrl.known_false_paths) == 0

    def test_prune_with_memory_alignment(self, golden_snapshot):
        ctrl = ReasoningController(enable_pruning=True)

        # Path aligns with episodic memory
        p_ok = ReasoningPath(steps=["Alice is 30"])
        episodic = [{"content": "Alice"}]

        # Path aligns with semantic memory
        p_also_ok = ReasoningPath(steps=["Charlie is 50"])
        semantic = [{"content": "Charlie"}]

        # Path aligns with neither -> will be pruned by current logic
        p_bad = ReasoningPath(steps=["Bob is 40"])

        pruned = ctrl.prune_contradictory_paths(
            [p_ok, p_also_ok, p_bad],
            episodic_memories=episodic,
            semantic_memories=semantic,
        )

        # Record golden snapshot for pruning logic
        golden_snapshot(
            test_name="math_reasoning_pruning",
            inputs={
                "paths": [{"steps": p.steps} for p in [p_ok, p_also_ok, p_bad]],
                "episodic": episodic,
                "semantic": semantic,
            },
            output={"pruned_count": 1, "remaining_steps": [p.steps for p in pruned]},
            metadata={"component": "ReasoningController"},
        )

        assert len(pruned) == 2
        assert p_ok in pruned
        assert p_also_ok in pruned
        assert p_bad not in pruned

    def test_pruning_disabled(self):
        ctrl = ReasoningController(enable_pruning=False)
        p = ReasoningPath(steps=["X"], contradictions=["Error"])
        pruned = ctrl.prune_contradictory_paths([p])
        assert len(pruned) == 1  # Should not prune if disabled

    def test_similarity_empty(self):
        p1 = ReasoningPath(steps=[])
        p2 = ReasoningPath(steps=["A"])
        assert p1.similarity_to(p2) == 0.0

        p3 = ReasoningPath(steps=["A"])
        p4 = ReasoningPath(steps=["!"])  # No words after split
        assert p3.similarity_to(p4) == 0.0

    def test_should_continue_golden(self, golden_snapshot):
        ctrl = ReasoningController()

        res_ok = ctrl.should_continue_reasoning(5, 0.8, 100)
        res_stop = ctrl.should_continue_reasoning(15, 0.8, 100)  # Max depth 12

        golden_snapshot(
            test_name="math_reasoning_should_continue",
            inputs={
                "case_ok": {"depth": 5, "unc": 0.8, "tokens": 100},
                "case_stop": {"depth": 15, "unc": 0.8, "tokens": 100},
            },
            output={"case_ok": res_ok, "case_stop": res_stop},
            metadata={"component": "ReasoningController"},
        )
