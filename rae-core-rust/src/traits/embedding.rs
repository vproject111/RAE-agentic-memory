use async_trait::async_trait;
use anyhow::Result;

#[async_trait]
pub trait IEmbeddingProvider: Send + Sync {
    async fn embed_text(&self, text: &str) -> Result<Vec<f32>>;
    async fn embed_batch(&self, texts: Vec<String>) -> Result<Vec<Vec<f32>>>;
    fn get_dimension(&self) -> usize;
}
