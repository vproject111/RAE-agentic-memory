use rae_core_rust::storage::graph::InMemoryGraphStore;
use rae_core_rust::traits::graph::IGraphStore;
use uuid::Uuid;
use std::collections::HashMap;

#[tokio::test]
async fn test_graph_basic() {
    let graph = InMemoryGraphStore::new();
    let tenant_id = "test_tenant";
    
    let id1 = Uuid::new_v4();
    let id2 = Uuid::new_v4();
    
    graph.create_node(id1, "Memory", tenant_id, None).await.expect("Failed to create node 1");
    graph.create_node(id2, "Reflection", tenant_id, None).await.expect("Failed to create node 2");
    
    graph.create_edge(id1, id2, "supports", tenant_id, 0.8, None).await.expect("Failed to create edge");
    
    let neighbors = graph.get_neighbors(id1, tenant_id, None, "both", 1).await.expect("Failed to get neighbors");
    assert_eq!(neighbors.len(), 1);
    assert_eq!(neighbors[0], id2);
}

#[tokio::test]
async fn test_shortest_path() {
    let graph = InMemoryGraphStore::new();
    let tenant_id = "test_tenant";
    
    let a = Uuid::new_v4();
    let b = Uuid::new_v4();
    let c = Uuid::new_v4();
    let d = Uuid::new_v4();
    
    graph.create_node(a, "T", tenant_id, None).await.unwrap();
    graph.create_node(b, "T", tenant_id, None).await.unwrap();
    graph.create_node(c, "T", tenant_id, None).await.unwrap();
    graph.create_node(d, "T", tenant_id, None).await.unwrap();
    
    // a -> b -> c -> d
    graph.create_edge(a, b, "L", tenant_id, 1.0, None).await.unwrap();
    graph.create_edge(b, c, "L", tenant_id, 1.0, None).await.unwrap();
    graph.create_edge(c, d, "L", tenant_id, 1.0, None).await.unwrap();
    
    let path = graph.shortest_path(a, d, tenant_id, 5).await.expect("Failed to find path");
    assert!(path.is_some());
    let path = path.unwrap();
    assert_eq!(path.len(), 4);
    assert_eq!(path, vec![a, b, c, d]);
}
