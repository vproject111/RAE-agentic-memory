use async_trait::async_trait;
use uuid::Uuid;
use serde_json::Value;
use std::collections::HashMap;
use anyhow::Result;

#[async_trait]
pub trait IGraphStore: Send + Sync {
    async fn create_node(
        &self,
        node_id: Uuid,
        node_type: &str,
        tenant_id: &str,
        properties: Option<HashMap<String, Value>>,
    ) -> Result<bool>;

    async fn create_edge(
        &self,
        source_id: Uuid,
        target_id: Uuid,
        edge_type: &str,
        tenant_id: &str,
        weight: f32,
        properties: Option<HashMap<String, Value>>,
    ) -> Result<bool>;

    async fn get_neighbors(
        &self,
        node_id: Uuid,
        tenant_id: &str,
        edge_type: Option<&str>,
        direction: &str,
        max_depth: usize,
    ) -> Result<Vec<Uuid>>;

    async fn delete_node(&self, node_id: Uuid, tenant_id: &str) -> Result<bool>;

    async fn delete_edge(
        &self,
        source_id: Uuid,
        target_id: Uuid,
        edge_type: &str,
        tenant_id: &str,
    ) -> Result<bool>;

    async fn shortest_path(
        &self,
        source_id: Uuid,
        target_id: Uuid,
        tenant_id: &str,
        max_depth: usize,
    ) -> Result<Option<Vec<Uuid>>>;

    async fn get_subgraph(
        &self,
        node_ids: Vec<Uuid>,
        tenant_id: &str,
        include_edges: bool,
    ) -> Result<Value>;
}
