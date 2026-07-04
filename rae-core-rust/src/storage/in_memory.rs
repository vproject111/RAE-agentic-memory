use async_trait::async_trait;
use uuid::Uuid;
use std::collections::HashMap;
use std::sync::RwLock;
use crate::traits::storage::{IMemoryStorage, MemoryRecord};
use crate::types::enums::MemoryLayer;
use serde_json::Value;
use anyhow::{Result, anyhow};

pub struct InMemoryStorage {
    memories: RwLock<HashMap<Uuid, MemoryRecord>>,
}

impl InMemoryStorage {
    pub fn new() -> Self {
        Self {
            memories: RwLock::new(HashMap::new()),
        }
    }
}

#[async_trait]
impl IMemoryStorage for InMemoryStorage {
    async fn store_memory(
        &self,
        tenant_id: &str,
        agent_id: &str,
        content: &str,
        layer: MemoryLayer,
        importance: f32,
        tags: Vec<String>,
        metadata: HashMap<String, Value>,
        _embedding: Option<Vec<f32>>,
        expires_at: Option<chrono::DateTime<chrono::Utc>>,
    ) -> Result<Uuid> {
        let id = Uuid::new_v4();
        let now = chrono::Utc::now();
        let record = MemoryRecord {
            id,
            tenant_id: tenant_id.to_string(),
            agent_id: agent_id.to_string(),
            content: content.to_string(),
            layer,
            importance,
            tags,
            metadata,
            created_at: now,
            updated_at: now,
            expires_at,
            last_accessed_at: None,
            access_count: 0,
        };

        let mut memories = self.memories.write().map_err(|_| anyhow!("Lock poisoned"))?;
        memories.insert(id, record);
        Ok(id)
    }

    async fn get_memory(&self, memory_id: Uuid, tenant_id: &str) -> Result<Option<MemoryRecord>> {
        let memories = self.memories.read().map_err(|_| anyhow!("Lock poisoned"))?;
        let record = memories.get(&memory_id).cloned();
        
        if let Some(ref r) = record {
            if r.tenant_id != tenant_id {
                return Ok(None);
            }
        }
        
        Ok(record)
    }

    async fn update_memory(
        &self,
        memory_id: Uuid,
        tenant_id: &str,
        _updates: HashMap<String, Value>,
    ) -> Result<bool> {
        // Simple implementation for now
        let mut memories = self.memories.write().map_err(|_| anyhow!("Lock poisoned"))?;
        if let Some(record) = memories.get_mut(&memory_id) {
            if record.tenant_id == tenant_id {
                record.updated_at = chrono::Utc::now();
                return Ok(true);
            }
        }
        Ok(false)
    }

    async fn delete_memory(&self, memory_id: Uuid, tenant_id: &str) -> Result<bool> {
        let mut memories = self.memories.write().map_err(|_| anyhow!("Lock poisoned"))?;
        if let Some(record) = memories.get(&memory_id) {
            if record.tenant_id == tenant_id {
                memories.remove(&memory_id);
                return Ok(true);
            }
        }
        Ok(false)
    }

    async fn list_memories(
        &self,
        tenant_id: &str,
        agent_id: Option<&str>,
        layer: Option<MemoryLayer>,
        _tags: Option<Vec<String>>,
        limit: usize,
        offset: usize,
    ) -> Result<Vec<MemoryRecord>> {
        let memories = self.memories.read().map_err(|_| anyhow!("Lock poisoned"))?;
        let filtered: Vec<MemoryRecord> = memories.values()
            .filter(|m| m.tenant_id == tenant_id)
            .filter(|m| agent_id.map_or(true, |a| m.agent_id == a))
            .filter(|m| layer.as_ref().map_or(true, |l| &m.layer == l))
            .skip(offset)
            .take(limit)
            .cloned()
            .collect();
        Ok(filtered)
    }

    async fn count_memories(
        &self,
        tenant_id: &str,
        agent_id: Option<&str>,
        layer: Option<MemoryLayer>,
    ) -> Result<usize> {
        let memories = self.memories.read().map_err(|_| anyhow!("Lock poisoned"))?;
        let count = memories.values()
            .filter(|m| m.tenant_id == tenant_id)
            .filter(|m| agent_id.map_or(true, |a| m.agent_id == a))
            .filter(|m| layer.as_ref().map_or(true, |l| &m.layer == l))
            .count();
        Ok(count)
    }

    async fn save_embedding(
        &self,
        _memory_id: Uuid,
        _model_name: &str,
        _embedding: Vec<f32>,
        _metadata: Option<HashMap<String, Value>>,
    ) -> Result<bool> {
        Ok(true)
    }
}
