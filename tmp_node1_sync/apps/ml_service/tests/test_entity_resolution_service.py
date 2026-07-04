from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from apps.ml_service.services.entity_resolution import EntityResolutionMLService


@pytest.fixture
def mock_embedding_service():
    with patch(
        "apps.ml_service.services.entity_resolution.EmbeddingMLService"
    ) as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        # Default embeddings for nodes
        mock_instance.generate_embeddings.return_value = [[0.1, 0.2], [0.3, 0.4]]
        yield mock_instance


@pytest.fixture
def mock_sklearn_components():
    with (
        patch(
            "apps.ml_service.services.entity_resolution.AgglomerativeClustering"
        ) as MockAgglomerativeClustering,
        patch(
            "apps.ml_service.services.entity_resolution.cosine_similarity"
        ) as MockCosineSimilarity,
    ):
        mock_agg_instance = MagicMock()
        MockAgglomerativeClustering.return_value = mock_agg_instance
        yield MockAgglomerativeClustering, mock_agg_instance, MockCosineSimilarity


@pytest.fixture
def entity_resolution_service(mock_embedding_service):
    service = EntityResolutionMLService(similarity_threshold=0.8)
    yield service


def test_entity_resolution_init(entity_resolution_service):
    """Test EntityResolutionMLService initialization."""
    assert entity_resolution_service.similarity_threshold == 0.8
    assert entity_resolution_service.embedding_service is not None


def test_resolve_entities_empty_nodes(
    entity_resolution_service, mock_embedding_service
):
    """Test resolving entities with an empty list of nodes."""
    merge_groups, statistics = entity_resolution_service.resolve_entities([])
    assert merge_groups == []
    assert statistics["nodes_processed"] == 0
    assert statistics["groups_found"] == 0
    assert statistics["reason"] == "insufficient_nodes"
    mock_embedding_service.generate_embeddings.assert_not_called()


def test_resolve_entities_multiple_nodes(
    entity_resolution_service,
    mock_sklearn_components,
    mock_embedding_service,
):
    """Test resolving entities with multiple nodes and mocked clustering."""
    (
        MockAgglomerativeClustering,
        mock_agg_instance,
        MockCosineSimilarity,
    ) = mock_sklearn_components

    nodes = [
        {"id": "node1", "label": "apple"},
        {"id": "node2", "label": "orange"},
        {"id": "node3", "label": "banana"},
        {"id": "node4", "label": "grape"},
    ]
    node_labels = [node["label"] for node in nodes]

    # Mock embeddings
    mock_embedding_service.generate_embeddings.return_value = [
        [0.1, 0.2],
        [0.11, 0.21],
        [0.9, 0.8],
        [0.91, 0.81],
    ]

    # Mock clustering result
    mock_agg_instance.fit_predict.return_value = np.array([0, 0, 1, 1])

    # Mock similarities for internal calculation
    MockCosineSimilarity.side_effect = [
        np.array([[0.95]]),  # apple-orange
        np.array([[0.92]]),  # banana-grape
    ]

    merge_groups, statistics = entity_resolution_service.resolve_entities(nodes)

    assert len(merge_groups) == 2
    assert statistics["nodes_processed"] == 4
    assert statistics["groups_found"] == 2

    mock_embedding_service.generate_embeddings.assert_called_once_with(node_labels)
    MockAgglomerativeClustering.assert_called_once()


def test_calculate_similarity_matrix(
    entity_resolution_service,
    mock_embedding_service,
    mock_sklearn_components,
):
    """Test calculate_similarity_matrix method."""
    _, _, MockCosineSimilarity = mock_sklearn_components
    labels = ["cat", "dog"]

    mock_embedding_service.generate_embeddings.return_value = [[0.1, 0.1], [0.2, 0.2]]
    MockCosineSimilarity.return_value = np.array([[1.0, 0.9], [0.9, 1.0]])

    matrix = entity_resolution_service.calculate_similarity_matrix(labels)

    assert matrix.shape == (2, 2)
    mock_embedding_service.generate_embeddings.assert_called_once_with(labels)
