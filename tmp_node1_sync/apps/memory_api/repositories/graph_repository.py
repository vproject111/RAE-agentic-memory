"""
GraphRepository - Data Access Layer for Knowledge Graph Operations.

This repository encapsulates all database operations related to the knowledge graph,
following the Repository/DAO pattern to separate data access from business logic.
"""

from typing import Any, Dict, List, Optional, Tuple, cast
from uuid import UUID, uuid4

import asyncpg
import structlog

from apps.memory_api.models.graph import GraphEdge, GraphNode

logger = structlog.get_logger(__name__)


class GraphRepository:
    """
    Repository for knowledge graph data access operations.

    Handles all SQL queries related to knowledge graph nodes and edges,
    including graph traversal algorithms (BFS/DFS).
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize graph repository.

        Args:
            pool: AsyncPG connection pool for database operations
        """
        self.pool = pool

    async def traverse_graph_bfs(
        self, start_node_ids: List[str], tenant_id: str, project_id: str, max_depth: int
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Perform breadth-first search graph traversal using recursive CTE.

        This method uses PostgreSQL's WITH RECURSIVE construct for efficient
        graph traversal, discovering nodes layer by layer from the start nodes.

        Args:
            start_node_ids: Node IDs to start traversal from
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier
            max_depth: Maximum depth to traverse (0 = start nodes only)

        Returns:
            Tuple of (discovered nodes, edges between discovered nodes)
        """
        async with self.pool.acquire() as conn:
            # Use recursive CTE for efficient BFS traversal
            node_records = await conn.fetch(
                """
                WITH RECURSIVE graph_traverse AS (
                    -- Base case: start nodes at depth 0
                    SELECT
                        n.id,
                        n.node_id,
                        n.label,
                        n.properties,
                        0 as depth
                    FROM knowledge_graph_nodes n
                    WHERE n.tenant_id = $1
                    AND n.project_id = $2
                    AND n.node_id = ANY($3)

                    UNION

                    -- Recursive case: traverse outgoing edges
                    SELECT
                        n.id,
                        n.node_id,
                        n.label,
                        n.properties,
                        gt.depth + 1
                    FROM graph_traverse gt
                    JOIN knowledge_graph_edges e ON gt.id = e.source_node_id
                    JOIN knowledge_graph_nodes n ON e.target_node_id = n.id
                    WHERE gt.depth < $4
                    AND n.tenant_id = $1
                    AND n.project_id = $2
                )
                SELECT * FROM (
                    SELECT DISTINCT ON (id) * FROM graph_traverse
                    ORDER BY id, depth
                ) as results
                ORDER BY depth, id;
                """,
                tenant_id,
                project_id,
                start_node_ids,
                max_depth,
            )

            # Convert database records to GraphNode models
            import json

            nodes = [
                GraphNode(
                    id=record["id"],
                    node_id=record["node_id"],
                    label=record["label"],
                    properties=(
                        json.loads(record["properties"])
                        if isinstance(record["properties"], str)
                        else record["properties"]
                    ),
                    depth=record["depth"],
                )
                for record in node_records
            ]

            # If no nodes found, return empty results
            if not nodes:
                logger.warning(
                    "bfs_traversal_no_nodes_found",
                    tenant_id=tenant_id,
                    project_id=project_id,
                    start_node_ids=start_node_ids,
                )
                return [], []

            # Get edges between discovered nodes
            edges = await self.get_edges_between_nodes(
                node_ids=[str(node.id) for node in nodes],
                tenant_id=tenant_id,
                project_id=project_id,
            )

            logger.info(
                "bfs_traversal_completed",
                tenant_id=tenant_id,
                project_id=project_id,
                nodes_found=len(nodes),
                edges_found=len(edges),
                max_depth=max_depth,
            )

            return nodes, edges

    async def traverse_graph_dfs(
        self, start_node_ids: List[str], tenant_id: str, project_id: str, max_depth: int
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Perform depth-first search graph traversal.

        Note: Current implementation uses the same SQL as BFS (WITH RECURSIVE).
        A true DFS would require different ordering or iterative processing.
        This provides the same result set with potentially different traversal order.

        Args:
            start_node_ids: Node IDs to start traversal from
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier
            max_depth: Maximum depth to traverse

        Returns:
            Tuple of (discovered nodes, edges between discovered nodes)
        """
        # For now, DFS uses same implementation as BFS
        # Future enhancement: implement true iterative DFS with stack
        return await self.traverse_graph_bfs(
            start_node_ids, tenant_id, project_id, max_depth
        )

    async def get_edges_between_nodes(
        self, node_ids: List[str], tenant_id: str, project_id: str
    ) -> List[GraphEdge]:
        """
        Retrieve all edges connecting nodes in the given set.

        Args:
            node_ids: Internal node IDs to find edges between
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier

        Returns:
            List of edges where both source and target are in node_ids
        """
        async with self.pool.acquire() as conn:
            edge_records = await conn.fetch(
                """
                SELECT
                    e.id,
                    e.source_node_id,
                    e.target_node_id,
                    e.relation,
                    e.properties
                FROM knowledge_graph_edges e
                WHERE e.tenant_id = $1
                AND e.project_id = $2
                AND e.source_node_id::text = ANY($3)
                AND e.target_node_id::text = ANY($3)
                """,
                tenant_id,
                project_id,
                node_ids,
            )

            import json

            edges = [
                GraphEdge(
                    source_id=record["source_node_id"],
                    target_id=record["target_node_id"],
                    relation=record["relation"],
                    properties=(
                        json.loads(record["properties"])
                        if isinstance(record["properties"], str)
                        else record["properties"]
                    ),
                )
                for record in edge_records
            ]

            return edges

    async def get_node_by_id(
        self, node_id: str, tenant_id: str, project_id: str
    ) -> Optional[GraphNode]:
        """
        Retrieve a single node by its node_id.

        Args:
            node_id: The node identifier
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier

        Returns:
            GraphNode if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT
                    id,
                    node_id,
                    label,
                    properties
                FROM knowledge_graph_nodes
                WHERE tenant_id = $1
                AND project_id = $2
                AND node_id = $3
                """,
                tenant_id,
                project_id,
                node_id,
            )

            if not record:
                return None

            return GraphNode(
                id=record["id"],
                node_id=record["node_id"],
                label=record["label"],
                properties=record["properties"],
                depth=0,
            )

    async def get_nodes_by_ids(
        self, node_ids: List[str], tenant_id: str, project_id: str
    ) -> List[GraphNode]:
        """
        Retrieve multiple nodes by their node_ids.

        Args:
            node_ids: List of node identifiers
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier

        Returns:
            List of found GraphNodes
        """
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT
                    id,
                    node_id,
                    label,
                    properties
                FROM knowledge_graph_nodes
                WHERE tenant_id = $1
                AND project_id = $2
                AND node_id = ANY($3)
                """,
                tenant_id,
                project_id,
                node_ids,
            )

            return [
                GraphNode(
                    id=record["id"],
                    node_id=record["node_id"],
                    label=record["label"],
                    properties=record["properties"],
                    depth=0,
                )
                for record in records
            ]

    async def find_relevant_communities(
        self, query: str, tenant_id: str, project_id: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find community nodes (Super-Nodes) relevant to the query using keyword matching.

        Args:
            query: Search query for keyword matching
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier
            limit: Maximum number of communities to return

        Returns:
            List of community node dictionaries
        """
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT id, label, properties
                FROM knowledge_graph_nodes
                WHERE tenant_id = $1 AND project_id = $2
                AND (properties->>'type') = 'community'
                AND (
                    label ILIKE '%' || $3 || '%'
                    OR (properties->>'summary') ILIKE '%' || $3 || '%'
                    OR (properties->>'themes')::text ILIKE '%' || $3 || '%'
                )
                LIMIT $4
                """,
                tenant_id,
                project_id,
                query,
                limit,
            )
            return [dict(r) for r in records]

    async def find_nodes_by_content_match(
        self, content: str, tenant_id: str, project_id: str, limit: int = 5
    ) -> List[str]:
        """
        Find graph nodes whose labels match content using fuzzy text matching.

        This method searches for nodes where the label appears in the content
        or vice versa, useful for entity linking from memory content.

        Args:
            content: Text content to search for matching entities
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier
            limit: Maximum number of nodes to return

        Returns:
            List of node_ids that match the content
        """
        async with self.pool.acquire() as conn:
            # Limit content length for performance
            content_sample = content[:500]

            nodes = await conn.fetch(
                """
                SELECT DISTINCT node_id
                FROM knowledge_graph_nodes
                WHERE tenant_id = $1
                AND project_id = $2
                AND (
                    $3 ILIKE '%' || label || '%'
                    OR label ILIKE '%' || $3 || '%'
                )
                LIMIT $4
                """,
                tenant_id,
                project_id,
                content_sample,
                limit,
            )

            return [node["node_id"] for node in nodes]

    async def create_node(
        self,
        tenant_id: str,
        project_id: str,
        node_id: str,
        label: str,
        properties: Dict[str, Any],
    ) -> bool:
        """
        Create a knowledge graph node with conflict handling.

        Args:
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier
            node_id: Unique node identifier
            label: Node label
            properties: Node properties as dictionary (will be stored as JSONB)

        Returns:
            True if node was created, False if it already existed
        """
        import json
        import uuid

        async with self.pool.acquire() as conn:
            # Ensure properties is JSON-serializable
            properties_json = json.dumps(properties) if properties else "{}"
            new_id = uuid.uuid4()

            result = await conn.execute(
                """
                INSERT INTO knowledge_graph_nodes
                (id, tenant_id, project_id, node_id, label, properties)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                ON CONFLICT (tenant_id, project_id, node_id) DO NOTHING
                """,
                new_id,
                tenant_id,
                project_id,
                node_id,
                label,
                properties_json,
            )

            return bool(result == "INSERT 0 1")

    async def create_edge(
        self,
        tenant_id: str,
        project_id: str,
        source_node_internal_id: int,
        target_node_internal_id: int,
        relation: str,
        properties: Dict[str, Any],
    ) -> bool:
        """
        Create a knowledge graph edge with conflict handling.

        Args:
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier
            source_node_internal_id: Internal database ID of source node
            target_node_internal_id: Internal database ID of target node
            relation: Relationship type
            properties: Edge properties as dictionary (will be stored as JSONB)

        Returns:
            True if edge was created, False if it already existed
        """
        import json
        import uuid

        async with self.pool.acquire() as conn:
            # Ensure properties is JSON-serializable
            properties_json = json.dumps(properties) if properties else "{}"
            new_id = uuid.uuid4()

            result = await conn.execute(
                """
                INSERT INTO knowledge_graph_edges
                (id, tenant_id, project_id, source_node_id, target_node_id, relation, properties)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                ON CONFLICT DO NOTHING
                """,
                new_id,
                tenant_id,
                project_id,
                source_node_internal_id,
                target_node_internal_id,
                relation,
                properties_json,
            )

            return bool(result == "INSERT 0 1")

    async def get_node_internal_id(
        self, tenant_id: str, project_id: str, node_id: str
    ) -> Optional[int]:
        """
        Get internal database ID for a node by its node_id.

        Args:
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier
            node_id: The node identifier

        Returns:
            Internal database ID (int) or None if not found
        """
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT id FROM knowledge_graph_nodes
                WHERE tenant_id = $1 AND project_id = $2 AND node_id = $3
                """,
                tenant_id,
                project_id,
                node_id,
            )

            return record["id"] if record else None

    async def store_graph_triples(
        self, triples: List[Dict[str, Any]], tenant_id: str, project_id: str
    ) -> Dict[str, int]:
        """
        Store multiple graph triples (nodes and edges) in a single transaction.

        This method handles the complete triple storage process:
        1. Creates source and target nodes (if they don't exist)
        2. Retrieves internal node IDs
        3. Creates edges between nodes

        Args:
            triples: List of triple dictionaries with keys: source, target, relation, confidence, metadata
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier

        Returns:
            Dictionary with counts: {"nodes_created": int, "edges_created": int}
        """
        nodes_created = 0
        edges_created = 0

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for triple in triples:
                    # Extract triple data
                    source = triple.get("source")
                    target = triple.get("target")
                    relation = triple.get("relation")
                    confidence = triple.get("confidence", 1.0)
                    metadata = triple.get("metadata", {})

                    if (
                        not isinstance(source, str)
                        or not isinstance(target, str)
                        or not isinstance(relation, str)
                    ):
                        logger.warning(
                            "invalid_triple_skipped",
                            source=source,
                            target=target,
                            relation=relation,
                        )
                        continue

                    # Create source node
                    node_created = await self.create_node(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        node_id=source,
                        label=source,
                        properties=metadata,
                    )
                    if node_created:
                        nodes_created += 1

                    # Create target node
                    node_created = await self.create_node(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        node_id=target,
                        label=target,
                        properties=metadata,
                    )
                    if node_created:
                        nodes_created += 1

                    # Get internal node IDs
                    source_internal_id = await self.get_node_internal_id(
                        tenant_id=tenant_id, project_id=project_id, node_id=source
                    )

                    target_internal_id = await self.get_node_internal_id(
                        tenant_id=tenant_id, project_id=project_id, node_id=target
                    )

                    # Create edge if both nodes exist
                    if source_internal_id and target_internal_id:
                        edge_properties = {"confidence": confidence, **metadata}

                        edge_created = await self.create_edge(
                            tenant_id=tenant_id,
                            project_id=project_id,
                            source_node_internal_id=source_internal_id,
                            target_node_internal_id=target_internal_id,
                            relation=relation,
                            properties=edge_properties,
                        )
                        if edge_created:
                            edges_created += 1

        logger.info(
            "graph_triples_stored",
            project_id=project_id,
            tenant_id=tenant_id,
            nodes_created=nodes_created,
            edges_created=edges_created,
        )

        return {"nodes_created": nodes_created, "edges_created": edges_created}

    async def get_all_nodes(
        self, tenant_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all nodes for a project.

        Used for entity resolution and community detection operations.

        Args:
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier

        Returns:
            List of node dictionaries with id, node_id, label
        """
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT id, node_id, label, properties
                FROM knowledge_graph_nodes
                WHERE tenant_id = $1 AND project_id = $2
                """,
                tenant_id,
                project_id,
            )
            return [dict(r) for r in records]

    async def get_all_edges(
        self, tenant_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all edges for a project.

        Used for community detection and graph analysis operations.

        Args:
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier

        Returns:
            List of edge dictionaries with source_node_id, target_node_id, relation
        """
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT source_node_id, target_node_id, relation, properties
                FROM knowledge_graph_edges
                WHERE tenant_id = $1 AND project_id = $2
                """,
                tenant_id,
                project_id,
            )
            return [dict(r) for r in records]

    async def update_node_label(self, node_internal_id: int, new_label: str) -> bool:
        """
        Update the label of a node.

        Used during entity resolution to update canonical names.

        Args:
            node_internal_id: Internal database ID of the node
            new_label: New label to assign

        Returns:
            True if update was successful
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE knowledge_graph_nodes
                SET label = $1
                WHERE id = $2
                """,
                new_label,
                node_internal_id,
            )

            return bool(result == "UPDATE 1")

    async def merge_node_edges(
        self, source_node_id: int, target_node_id: int
    ) -> Dict[str, int]:
        """
        Merge edges from source node to target node.

        Moves all edges (incoming and outgoing) from source to target.
        Uses ON CONFLICT DO NOTHING to handle duplicate edges.

        Args:
            source_node_id: Internal ID of source node (to be merged)
            target_node_id: Internal ID of target node (merge destination)

        Returns:
            Dictionary with counts: {"outgoing_updated": int, "incoming_updated": int}
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Move outgoing edges
                outgoing_result = await conn.execute(
                    """
                    UPDATE knowledge_graph_edges
                    SET source_node_id = $1
                    WHERE source_node_id = $2
                    """,
                    target_node_id,
                    source_node_id,
                )

                # Move incoming edges
                incoming_result = await conn.execute(
                    """
                    UPDATE knowledge_graph_edges
                    SET target_node_id = $1
                    WHERE target_node_id = $2
                    """,
                    target_node_id,
                    source_node_id,
                )

                # Parse results (format: "UPDATE N")
                outgoing_count = (
                    int(outgoing_result.split()[-1]) if outgoing_result else 0
                )
                incoming_count = (
                    int(incoming_result.split()[-1]) if incoming_result else 0
                )

                logger.info(
                    "edges_merged",
                    source_node_id=source_node_id,
                    target_node_id=target_node_id,
                    outgoing=outgoing_count,
                    incoming=incoming_count,
                )

                return {
                    "outgoing_updated": outgoing_count,
                    "incoming_updated": incoming_count,
                }

    async def delete_node_edges(self, node_internal_id: int) -> int:
        """
        Delete all edges connected to a node (both incoming and outgoing).

        Args:
            node_internal_id: Internal database ID of the node

        Returns:
            Number of edges deleted
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM knowledge_graph_edges
                WHERE source_node_id = $1 OR target_node_id = $1
                """,
                node_internal_id,
            )

            # Parse result (format: "DELETE N")
            count = int(result.split()[-1]) if result else 0

            logger.info(
                "node_edges_deleted", node_id=node_internal_id, edges_deleted=count
            )

            return count

    async def delete_node(self, node_internal_id: int) -> bool:
        """
        Delete a node from the knowledge graph.

        Note: Edges should be deleted first using delete_node_edges().

        Args:
            node_internal_id: Internal database ID of the node

        Returns:
            True if node was deleted
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM knowledge_graph_nodes
                WHERE id = $1
                """,
                node_internal_id,
            )

            success = bool(result == "DELETE 1")

            if success:
                logger.info("node_deleted", node_id=node_internal_id)
            else:
                logger.warning("node_deletion_failed", node_id=node_internal_id)

            return success

    async def upsert_node(
        self,
        tenant_id: str,
        project_id: str,
        node_id: str,
        label: str,
        properties: Dict[str, Any],
    ) -> UUID | int:
        """
        Insert or update a node (upsert operation).

        If node exists, updates label and properties.
        If node doesn't exist, creates it.

        Args:
            tenant_id: Tenant identifier for data isolation
            project_id: Project identifier
            node_id: Unique node identifier
            label: Node label
            properties: Node properties as dictionary

        Returns:
            Internal database ID of the node
        """
        import json

        async with self.pool.acquire() as conn:
            # Ensure properties is JSON-serializable
            properties_json = json.dumps(properties) if properties else "{}"
            technical_id = uuid4()

            record = await conn.fetchrow(
                """
                INSERT INTO knowledge_graph_nodes
                (id, tenant_id, project_id, node_id, label, properties)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                ON CONFLICT (tenant_id, project_id, node_id)
                DO UPDATE SET
                    label = EXCLUDED.label,
                    properties = EXCLUDED.properties
                RETURNING id
                """,
                technical_id,
                tenant_id,
                project_id,
                node_id,
                label,
                properties_json,
            )

            internal_id = cast(UUID | int, record["id"])

            logger.info(
                "node_upserted",
                tenant_id=tenant_id,
                project_id=project_id,
                node_id=node_id,
                internal_id=internal_id,
            )

            return internal_id
