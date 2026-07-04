use rae_core_rust::storage::in_memory::InMemoryStorage;
use rae_core_rust::traits::storage::IMemoryStorage;
use rae_core_rust::types::enums::MemoryLayer;
use std::collections::HashMap;
use uuid::Uuid;

#[tokio::test]
async fn test_in_memory_storage_basic() {
    let storage = InMemoryStorage::new();
    let tenant_id = "test_tenant";
    let agent_id = "test_agent";
    let content = "Hello RAE";
    
    let id = storage.store_memory(
        tenant_id,
        agent_id,
        content,
        MemoryLayer::Sensory,
        1.0,
        vec!["test".to_string()],
        HashMap::new(),
        None,
        None,
    ).await.expect("Failed to store memory");

    let record = storage.get_memory(id, tenant_id).await.expect("Failed to get memory");
    assert!(record.is_some());
    let record = record.unwrap();
    assert_eq!(record.content, content);
    assert_eq!(record.tenant_id, tenant_id);
    assert_eq!(record.agent_id, agent_id);
}

#[tokio::test]
async fn test_tenant_isolation() {
    let storage = InMemoryStorage::new();
    let tenant1 = "tenant1";
    let tenant2 = "tenant2";
    
    let id = storage.store_memory(
        tenant1,
        "agent",
        "private content",
        MemoryLayer::Working,
        1.0,
        vec![],
        HashMap::new(),
        None,
        None,
    ).await.expect("Failed to store");

    let record_for_tenant2 = storage.get_memory(id, tenant2).await.expect("Failed to get");
    assert!(record_for_tenant2.is_none());

    let record_for_tenant1 = storage.get_memory(id, tenant1).await.expect("Failed to get");
    assert!(record_for_tenant1.is_some());
}

#[tokio::test]
async fn test_concurrency_storage() {
    let storage = std::sync::Arc::new(InMemoryStorage::new());
    let mut handles = vec![];

    for i in 0..100 {
        let storage_clone = storage.clone();
        let handle = tokio::spawn(async move {
            storage_clone.store_memory(
                "tenant",
                &format!("agent_{}", i),
                &format!("content_{}", i),
                MemoryLayer::Working,
                0.5,
                vec![],
                HashMap::new(),
                None,
                None,
            ).await
        });
        handles.push(handle);
    }

    for handle in handles {
        let res = handle.await.expect("Task failed");
        assert!(res.is_ok());
    }

    let count = storage.count_memories("tenant", None, None).await.expect("Failed to count");
    assert_eq!(count, 100);
}
