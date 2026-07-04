use async_trait::async_trait;
use uuid::Uuid;
use serde_json::Value;
use crate::types::enums::MemoryLayer;
use std::collections::HashMap;
use anyhow::Result;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct MemoryRecord {
    pub id: Uuid,
    pub tenant_id: String,
    pub agent_id: String,
    pub content: String,
    pub layer: MemoryLayer,
    pub importance: f32,
    pub tags: Vec<String>,
    pub metadata: HashMap<String, Value>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
    pub expires_at: Option<chrono::DateTime<chrono::Utc>>,
    pub last_accessed_at: Option<chrono::DateTime<chrono::Utc>>,
    pub access_count: i32,
}

#[async_trait]
pub trait IMemoryStorage: Send + Sync {
    async fn store_memory(
        &self,
        tenant_id: &str,
        agent_id: &str,
        content: &str,
        layer: MemoryLayer,
        importance: f32,
        tags: Vec<String>,
        metadata: HashMap<String, Value>,
        embedding: Option<Vec<f32>>,
        expires_at: Option<chrono::DateTime<chrono::Utc>>,
    ) -> Result<Uuid>;

    async fn get_memory(&self, memory_id: Uuid, tenant_id: &str) -> Result<Option<MemoryRecord>>;

    async fn update_memory(
        &self,
        memory_id: Uuid,
        tenant_id: &str,
        updates: HashMap<String, Value>,
    ) -> Result<bool>;

    async fn delete_memory(&self, memory_id: Uuid, tenant_id: &str) -> Result<bool>;

    async fn list_memories(
        &self,
        tenant_id: &str,
        agent_id: Option<&str>,
        layer: Option<MemoryLayer>,
        tags: Option<Vec<String>>,
        limit: usize,
        offset: usize,
    ) -> Result<Vec<MemoryRecord>>;

    async fn count_memories(
        &self,
        tenant_id: &str,
        agent_id: Option<&str>,
        layer: Option<MemoryLayer>,
    ) -> Result<usize>;

    async fn save_embedding(
        &self,
        memory_id: Uuid,
        model_name: &str,
        embedding: Vec<f32>,
        metadata: Option<HashMap<String, Value>>,
    ) -> Result<bool>;
}
