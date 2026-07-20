from rae_core.math.features import Features
from rae_core.math.features_v2 import FeatureExtractorV2, FeaturesV2
from rae_core.math.types import TaskType


def test_features_v2_affinities():
    f = FeaturesV2(task_type=TaskType.MEMORY_RETRIEVE)
    assert f.get_task_affinity_l1() == 0.8
    assert f.get_task_affinity_l2() == 0.5

    f.task_type = TaskType.MEMORY_STORE
    assert f.get_task_affinity_l1() == 0.9
    assert f.get_task_affinity_l2() == 0.3

    f.task_type = TaskType.CONTEXT_SELECT
    assert f.get_task_affinity_l1() == 0.7
    assert f.get_task_affinity_l2() == 0.6

    f.task_type = TaskType.MEMORY_CONSOLIDATE
    assert f.get_task_affinity_l1() == 0.4
    assert f.get_task_affinity_l2() == 0.8

    f.task_type = TaskType.REFLECTION_LIGHT
    assert f.get_task_affinity_l1() == 0.6
    assert f.get_task_affinity_l2() == 0.7

    f.task_type = TaskType.REFLECTION_DEEP
    assert f.get_task_affinity_l1() == 0.2
    assert f.get_task_affinity_l2() == 0.9

    f.task_type = TaskType.GRAPH_UPDATE
    assert f.get_task_affinity_l1() == 0.5
    assert f.get_task_affinity_l2() == 0.7


def test_features_v2_from_base():
    base = Features(task_type=TaskType.MEMORY_RETRIEVE, memory_count=10)
    v2 = FeaturesV2.from_features(base, is_first_turn=True)
    assert v2.task_type == TaskType.MEMORY_RETRIEVE
    assert v2.memory_count == 10
    assert v2.is_first_turn is True


def test_feature_extractor_v2_empty_query():
    extractor = FeatureExtractorV2()
    f = extractor.extract("")
    assert f.task_type == TaskType.MEMORY_RETRIEVE


def test_feature_extractor_v2_symbols():
    extractor = FeatureExtractorV2()
    # Query with symbols (letters + digits) and hyphens
    f = extractor.extract("Search for item-123 and 0xABC")
    # We can't easily check internal 'symbols' list but we can check it doesn't crash
    # and it might affect some metrics if they were implemented using it.
    assert f.task_type == TaskType.MEMORY_RETRIEVE
