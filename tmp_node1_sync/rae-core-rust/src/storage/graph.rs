use async_trait::async_trait;
use uuid::Uuid;
use std::collections::{HashMap, HashSet};
use std::sync::RwLock;
use crate::traits::graph::IGraphStore;
use serde_json::Value;
use anyhow::{Result, anyhow};

#[derive(Debug, Clone)]
struct Node {
    id: Uuid,
    node_type: String,
    properties: HashMap<String, Value>,
}

#[derive(Debug, Clone)]
struct Edge {
    source_id: Uuid,
    target_id: Uuid,
    edge_type: String,
    weight: f32,
    properties: HashMap<String, Value>,
}

pub struct InMemoryGraphStore {
    nodes: RwLock<HashMap<String, HashMap<Uuid, Node>>>, // tenant_id -> node_id -> Node
    edges: RwLock<HashMap<String, Vec<Edge>>>,           // tenant_id -> [Edge]
}

impl InMemoryGraphStore {
    pub fn new() -> Self {
        Self {
            nodes: RwLock::new(HashMap::new()),
            edges: RwLock::new(HashMap::new()),
        }
    }
}

#[async_trait]
impl IGraphStore for InMemoryGraphStore {
    async fn create_node(
        &self,
        node_id: Uuid,
        node_type: &str,
        tenant_id: &str,
        properties: Option<HashMap<String, Value>>,
    ) -> Result<bool> {
        let mut all_nodes = self.nodes.write().map_err(|_| anyhow!("Lock poisoned"))?;
        let tenant_nodes = all_nodes.entry(tenant_id.to_string()).or_insert_with(HashMap::new());
        
        tenant_nodes.insert(node_id, Node {
            id: node_id,
            node_type: node_type.to_string(),
            properties: properties.unwrap_or_default(),
        });
        
        Ok(true)
    }

    async fn create_edge(
        &self,
        source_id: Uuid,
        target_id: Uuid,
        edge_type: &str,
        tenant_id: &str,
        weight: f32,
        properties: Option<HashMap<String, Value>>,
    ) -> Result<bool> {
        let mut all_edges = self.edges.write().map_err(|_| anyhow!("Lock poisoned"))?;
        let tenant_edges = all_edges.entry(tenant_id.to_string()).or_insert_with(Vec::new());
        
        tenant_edges.push(Edge {
            source_id,
            target_id,
            edge_type: edge_type.to_string(),
            weight,
            properties: properties.unwrap_or_default(),
        });
        
        Ok(true)
    }

    async fn get_neighbors(
        &self,
        node_id: Uuid,
        tenant_id: &str,
        edge_type: Option<&str>,
        direction: &str,
        _max_depth: usize, // Simplification for now
    ) -> Result<Vec<Uuid>> {
        let all_edges = self.edges.read().map_err(|_| anyhow!("Lock poisoned"))?;
        let tenant_edges = match all_edges.get(tenant_id) {
            Some(e) => e,
            None => return Ok(Vec::new()),
        };

        let mut neighbors = HashSet::new();
        for edge in tenant_edges {
            if edge_type.map_or(true, |t| edge.edge_type == t) {
                match direction {
                    "out" => if edge.source_id == node_id { neighbors.insert(edge.target_id); },
                    "in" => if edge.target_id == node_id { neighbors.insert(edge.source_id); },
                    _ => {
                        if edge.source_id == node_id { neighbors.insert(edge.target_id); }
                        else if edge.target_id == node_id { neighbors.insert(edge.source_id); }
                    }
                }
            }
        }

        Ok(neighbors.into_iter().collect())
    }

    async fn delete_node(&self, node_id: Uuid, tenant_id: &str) -> Result<bool> {
        let mut all_nodes = self.nodes.write().map_err(|_| anyhow!("Lock poisoned"))?;
        let mut all_edges = self.edges.write().map_err(|_| anyhow!("Lock poisoned"))?;

        let removed = if let Some(tenant_nodes) = all_nodes.get_mut(tenant_id) {
            tenant_nodes.remove(&node_id).is_some()
        } else {
            false
        };

        if let Some(tenant_edges) = all_edges.get_mut(tenant_id) {
            tenant_edges.retain(|e| e.source_id != node_id && e.target_id != node_id);
        }

        Ok(removed)
    }

    async fn delete_edge(
        &self,
        source_id: Uuid,
        target_id: Uuid,
        edge_type: &str,
        tenant_id: &str,
    ) -> Result<bool> {
        let mut all_edges = self.edges.write().map_err(|_| anyhow!("Lock poisoned"))?;
        if let Some(tenant_edges) = all_edges.get_mut(tenant_id) {
            let initial_len = tenant_edges.len();
            tenant_edges.retain(|e| !(e.source_id == source_id && e.target_id == target_id && e.edge_type == edge_type));
            return Ok(tenant_edges.len() < initial_len);
        }
        Ok(false)
    }

    async fn shortest_path(
        &self,
        source_id: Uuid,
        target_id: Uuid,
        tenant_id: &str,
        max_depth: usize,
    ) -> Result<Option<Vec<Uuid>>> {
        // BFS for shortest path
        if source_id == target_id {
            return Ok(Some(vec![source_id]));
        }

        let all_edges = self.edges.read().map_err(|_| anyhow!("Lock poisoned"))?;
        let tenant_edges = match all_edges.get(tenant_id) {
            Some(e) => e,
            None => return Ok(None),
        };

        let mut queue = std::collections::VecDeque::new();
        queue.push_back(vec![source_id]);
        
        let mut visited = HashSet::new();
        visited.insert(source_id);

        while let Some(path) = queue.pop_front() {
            if path.len() > max_depth {
                continue;
            }

            let current = *path.last().unwrap();
            for edge in tenant_edges {
                let neighbor = if edge.source_id == current {
                    Some(edge.target_id)
                } else if edge.target_id == current {
                    Some(edge.source_id)
                } else {
                    None
                };

                if let Some(n) = neighbor {
                    if n == target_id {
                        let mut final_path = path.clone();
                        final_path.push(n);
                        return Ok(Some(final_path));
                    }
                    if !visited.contains(&n) {
                        visited.insert(n);
                        let mut next_path = path.clone();
                        next_path.push(n);
                        queue.push_back(next_path);
                    }
                }
            }
        }

        Ok(None)
    }

    async fn get_subgraph(
        &self,
        node_ids: Vec<Uuid>,
        tenant_id: &str,
        include_edges: bool,
    ) -> Result<Value> {
        let all_nodes = self.nodes.read().map_err(|_| anyhow!("Lock poisoned"))?;
        let all_edges = self.edges.read().map_err(|_| anyhow!("Lock poisoned"))?;

        let tenant_nodes = all_nodes.get(tenant_id);
        let tenant_edges = all_edges.get(tenant_id);

        let mut nodes_out = Vec::new();
        let node_set: HashSet<Uuid> = node_ids.iter().cloned().collect();

        if let Some(tn) = tenant_nodes {
            for id in &node_ids {
                if let Some(node) = tn.get(id) {
                    nodes_out.push(serde_json::json!({
                        "id": node.id,
                        "type": node.node_type,
                        "properties": node.properties
                    }));
                }
            }
        }

        let mut edges_out = Vec::new();
        if include_edges {
            if let Some(te) = tenant_edges {
                for edge in te {
                    if node_set.contains(&edge.source_id) && node_set.contains(&edge.target_id) {
                        edges_out.push(serde_json::json!({
                            "source": edge.source_id,
                            "target": edge.target_id,
                            "type": edge.edge_type,
                            "weight": edge.weight,
                            "properties": edge.properties
                        }));
                    }
                }
            }
        }

        Ok(serde_json::json!({
            "nodes": nodes_out,
            "edges": edges_out
        }))
    }
}
