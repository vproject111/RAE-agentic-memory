use async_trait::async_trait;
use uuid::Uuid;
use serde_json::Value;
use std::collections::HashMap;
use anyhow::Result;
use crate::types::enums::MemoryLayer;

#[async_trait]
pub trait IVectorStore: Send + Sync {
    async fn store_vector(
        &self,
        memory_id: Uuid,
        embedding: Vec<f32>,
        tenant_id: &str,
        metadata: Option<HashMap<String, Value>>,
    ) -> Result<bool>;

    async fn search_similar(
        &self,
        query_embedding: Vec<f32>,
        tenant_id: &str,
        layer: Option<MemoryLayer>,
        limit: usize,
        score_threshold: Option<f32>,
    ) -> Result<Vec<(Uuid, f32)>>;

    async fn delete_vector(&self, memory_id: Uuid, tenant_id: &str) -> Result<bool>;

    async fn get_vector(&self, memory_id: Uuid, tenant_id: &str) -> Result<Option<Vec<f32>>>;
}
