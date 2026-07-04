use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum MemoryLayer {
    Sensory,
    Working,
    Episodic,
    Semantic,
    Reflective,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum MemoryType {
    Text,
    Code,
    Image,
    Document,
    Conversation,
    Reflection,
    Entity,
    Relationship,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ContextFormat {
    Conversational,
    Structured,
    Minimal,
    Detailed,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum DistanceMetric {
    #[serde(rename = "Cosine")]
    Cosine,
    #[serde(rename = "Euclid")]
    Euclid,
    #[serde(rename = "Dot")]
    Dot,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ReflectionType {
    Consolidation,
    Pattern,
    Anomaly,
    Meta,
}
