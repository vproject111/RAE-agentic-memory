"""
Entity Resolution ML Service - ML operations for entity deduplication.

This service handles the computationally expensive parts:
- Embedding generation (via API)
- Similarity clustering

The main API retains orchestration, database operations, and LLM calls.
"""

from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import structlog
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from apps.ml_service.services.embedding_service import EmbeddingMLService

logger = structlog.get_logger(__name__)


class EntityResolutionMLService:
    """
    ML service for entity resolution.

    Handles embedding generation (via API) and clustering to identify
    potential entity duplicates.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize entity resolution ML service.

        Args:
            similarity_threshold: Minimum cosine similarity for clustering
        """
        self.similarity_threshold = similarity_threshold
        # Uses the updated API-based embedding service
        self.embedding_service = EmbeddingMLService()

    def resolve_entities(
        self, nodes: List[Dict[str, Any]], similarity_threshold: Optional[float] = None
    ) -> Tuple[List[List[str]], Dict[str, Any]]:
        """
        Identify groups of similar entities that should potentially be merged.

        Args:
            nodes: List of node dictionaries with 'id' and 'label' keys
            similarity_threshold: Override default similarity threshold

        Returns:
            Tuple of (merge_groups, statistics)
        """
        if not nodes or len(nodes) < 2:
            logger.info("not_enough_nodes_for_clustering", count=len(nodes))
            return [], {
                "nodes_processed": len(nodes),
                "groups_found": 0,
                "reason": "insufficient_nodes",
            }

        threshold = similarity_threshold or self.similarity_threshold

        # Extract labels for embedding
        node_labels = [node.get("label", "") for node in nodes]
        node_ids = [node.get("id", "") for node in nodes]

        logger.info("generating_embeddings", node_count=len(nodes), threshold=threshold)

        # Generate embeddings via API-based service
        embeddings_list = self.embedding_service.generate_embeddings(node_labels)
        embeddings = np.array(embeddings_list)

        # Perform clustering
        distance_threshold = 1 - threshold

        clustering = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=distance_threshold,
        )

        cluster_labels = clustering.fit_predict(embeddings)

        # Group nodes by cluster
        clusters: Dict[int, List[int]] = {}
        for idx, label in enumerate(cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)

        # Build merge groups (only clusters with 2+ nodes)
        merge_groups = []
        group_similarities = []

        for cluster_id, indices in clusters.items():
            if len(indices) < 2:
                continue

            # Calculate minimum similarity within cluster
            cluster_embeddings = [embeddings[i] for i in indices]
            min_sim = self._calculate_min_similarity(cluster_embeddings)

            # Build group with node IDs
            group_node_ids = [node_ids[i] for i in indices]
            merge_groups.append(group_node_ids)
            group_similarities.append(min_sim)

            logger.info(
                "cluster_found",
                cluster_id=cluster_id,
                size=len(indices),
                min_similarity=min_sim,
                nodes=[node_labels[i] for i in indices],
            )

        statistics = {
            "nodes_processed": len(nodes),
            "groups_found": len(merge_groups),
            "total_clusters": len(clusters),
            "similarity_threshold": threshold,
            "average_group_similarity": (
                float(np.mean(group_similarities)) if group_similarities else 0.0
            ),
        }

        logger.info(
            "entity_resolution_completed",
            groups_found=len(merge_groups),
            nodes_processed=len(nodes),
        )

        return merge_groups, statistics

    def _calculate_min_similarity(self, embeddings: List[np.ndarray]) -> float:
        """
        Calculate minimum pairwise cosine similarity within a group.
        """
        min_sim = 1.0

        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                if sim < min_sim:
                    min_sim = sim

        return float(min_sim)

    def calculate_similarity_matrix(self, labels: List[str]) -> np.ndarray:
        """
        Calculate pairwise similarity matrix for entity labels.
        """
        embeddings_list = self.embedding_service.generate_embeddings(labels)
        embeddings = np.array(embeddings_list)
        similarity_matrix = cosine_similarity(embeddings)
        return cast(np.ndarray, similarity_matrix)
