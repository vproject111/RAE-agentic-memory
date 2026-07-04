# Research Documentation Portal

**Welcome, Researcher!** 🔬

This portal is designed for researchers, academics, and scientists exploring RAE (Reflective Agentic-memory Engine) for research purposes. Whether you're studying memory architectures, evaluating cognitive systems, benchmarking AI agents, or writing academic papers, you'll find comprehensive technical documentation, mathematical foundations, and reproducible experiments here.

## 🚀 Quick Start (15 minutes)

**New to RAE Research?** Start here:

1. **[Mathematical Foundations](#-mathematical-foundations)**
   - Memory encoding and retrieval models
   - Vector similarity metrics
   - Graph algorithms and complexity
   - Reflection formalization

2. **[Benchmarking & Evaluation](#-benchmarking--evaluation)**
   - Standard evaluation datasets
   - Performance metrics
   - Reproducible experiments
   - Comparison with baselines

3. **[Research Use Cases](#-research-use-cases)**
   - Cognitive architectures
   - Memory consolidation studies
   - Multi-agent systems
   - Knowledge graph research

## 📚 Core Research Areas

### Memory Architecture Research

| Topic | Description | Documentation |
|-------|-------------|---------------|
| **Multi-Layer Memory** | Episodic, Working, Semantic, LTM | [Memory Layers](../../reference/architecture/memory-layers.md) |
| **Memory Consolidation** | Autonomous reflection mechanisms | [Reflection Engine](../../REFLECTION_MODE.md) |
| **Hybrid Search** | Vector + keyword + re-ranking | [Hybrid Search](../../reference/architecture/hybrid-search.md) |
| **Embedding Models** | Sentence transformers, custom models | [Embeddings](../../reference/services/embedding-service.md) |
| **Memory Decay** | Forgetting curves and retention | [Decay Models](#memory-decay-models) |

### Graph & Knowledge Representation

| Topic | Description | Documentation |
|-------|-------------|---------------|
| **GraphRAG** | Knowledge graph augmented retrieval | [GraphRAG](../../reference/services/graph-service.md) |
| **Entity Resolution** | Deduplication and linking | [Entity Resolution](#entity-resolution) |
| **Temporal Graphs** | Time-aware knowledge graphs | [Temporal Graphs](../enterprise/GRAPH_ENHANCED_GUIDE.md#temporal-graphs) |
| **Graph Algorithms** | BFS, DFS, shortest path, centrality | [Graph Algorithms](#graph-algorithms) |

### LLM & Agent Research

| Topic | Description | Documentation |
|-------|-------------|---------------|
| **LLM Orchestration** | Multi-model routing and fallbacks | [LLM Orchestrator](../../project-design/active/LLM_orchestrator/LLM_ORCHESTRATOR.md) |
| **Prompt Engineering** | Systematic prompt optimization | [Prompt Patterns](#prompt-engineering) |
| **Agent Memory** | Persistent agent state | [Agent Memory](#agent-memory-patterns) |
| **Multi-Agent Systems** | Shared and isolated memory | [Multi-Agent](#multi-agent-research) |

## 🔬 Mathematical Foundations

### Memory Encoding

**Vector Representation:**

Memory content is encoded as dense vectors in high-dimensional space:

```
m_i = φ(c_i)  where φ: C → ℝ^d
```

Where:
- `m_i` = memory vector (d-dimensional)
- `c_i` = content (text/multimodal)
- `φ` = embedding function
- `d` = embedding dimension (typically 384, 768, or 1536)

**Similarity Function:**

Cosine similarity between memories:

```
sim(m_i, m_j) = (m_i · m_j) / (||m_i|| × ||m_j||)
```

**Retrieval Function:**

Given query `q`, retrieve top-k memories:

```
R(q, k) = argmax_{M_k ⊂ M} Σ_{m_i ∈ M_k} sim(φ(q), m_i)
```

### Hybrid Search Model

**Fusion Function:**

RAE combines dense (vector) and sparse (BM25) retrieval:

```
score(m_i, q) = α · score_dense(m_i, q) + (1-α) · score_sparse(m_i, q)
```

Where:
- `α ∈ [0,1]` = fusion weight (default: 0.5)
- `score_dense` = cosine similarity
- `score_sparse` = BM25 score

**Re-ranking:**

Cross-encoder re-ranks top-k results:

```
rank(m_i) = σ(W · [φ_q(q) ⊕ φ_m(m_i)] + b)
```

Where:
- `σ` = sigmoid activation
- `⊕` = concatenation
- `W, b` = learned parameters

**Expected Complexity:**

| Operation | Time Complexity | Space Complexity |
|-----------|-----------------|------------------|
| **Encode query** | O(l) | O(d) |
| **Vector search** | O(n·d) | O(n·d) |
| **BM25 search** | O(n·avg_len) | O(n·vocab) |
| **Re-ranking** | O(k·l) | O(k·d) |
| **Total** | O(n·d + k·l) | O(n·d) |

Where: n = corpus size, d = embedding dim, k = top-k, l = seq length

### Memory Consolidation Model

**Reflection Function:**

Given episodic memories E, generate semantic memory S:

```
S = ψ(E) where ψ: 2^E → S
```

**Pattern Detection:**

Identify recurring patterns using clustering:

```
P = {p_1, ..., p_m} = cluster(E, sim, threshold)
```

**Abstraction Level:**

Memories organized hierarchically by abstraction:

```
M = M_0 (raw) ∪ M_1 (summarized) ∪ M_2 (abstracted) ∪ ... ∪ M_n (principles)
```

**Consolidation Trigger:**

Reflection triggered when:

```
|E_new| ≥ θ_count  OR  t - t_last ≥ θ_time  OR  entropy(E) ≥ θ_entropy
```

### Memory Decay Models

**Ebbinghaus Forgetting Curve:**

Memory strength decays over time:

```
R(t) = e^(-t/S)
```

Where:
- `R(t)` = retention at time t
- `S` = memory strength (determined by importance, recency, frequency)

**Importance-Weighted Decay:**

```
S(m_i) = importance(m_i) × recency(m_i) × frequency(m_i)
```

**Decay Implementation:**

```python
# Memories automatically receive importance scores
importance(m_i) = α_1·LLM_score(m_i) + α_2·graph_centrality(m_i) + α_3·user_score(m_i)

# Decay applied during retrieval
score_adjusted(m_i, q, t) = score(m_i, q) × R(t - t_created(m_i))
```

## 📊 Benchmarking & Evaluation

### Standard Benchmarks

**RAE Benchmark Suite:**

| Benchmark | Task | Metrics | Dataset |
|-----------|------|---------|---------|
| **Memory Recall** | Retrieve specific facts | Recall@k, MRR | Custom |
| **Semantic Search** | Find conceptually similar | NDCG@k, MAP | MS MARCO |
| **Multi-hop Reasoning** | Chain facts together | Accuracy, F1 | HotpotQA |
| **Temporal Reasoning** | Time-aware queries | Accuracy | TempQuestions |
| **Memory Consolidation** | Quality of reflections | ROUGE, BERTScore | Custom |

**Download Benchmark Data:**

```bash
# Clone evaluation suite
git clone https://github.com/dreamsoft-pro/rae-benchmarks.git
cd rae-benchmarks

# Download datasets
python scripts/download_datasets.py --all

# Run benchmarks
python run_benchmarks.py --model rae --config configs/default.yaml
```

### Performance Metrics

**Information Retrieval Metrics:**

```python
# Precision@k
P@k = (# relevant in top-k) / k

# Recall@k
R@k = (# relevant in top-k) / (# total relevant)

# Mean Reciprocal Rank
MRR = (1/|Q|) Σ (1 / rank_i)

# Normalized Discounted Cumulative Gain
NDCG@k = DCG@k / IDCG@k
```

**Latency Metrics:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Encoding latency** | < 50ms | Query to embedding |
| **Search latency** | < 100ms | Embedding to results |
| **End-to-end latency** | < 200ms | Query to response |
| **P95 latency** | < 500ms | 95th percentile |
| **P99 latency** | < 1000ms | 99th percentile |

**Memory Efficiency:**

```python
# Embedding storage per memory
storage_per_memory = embedding_dim × 4 bytes (float32)
                   = 768 × 4 = 3,072 bytes ≈ 3 KB

# For 1M memories
total_storage = 1M × 3 KB = 3 GB (embeddings only)
              + metadata + content storage
```

### Reproducible Experiments

**Experiment Configuration:**

```yaml
# experiments/config.yaml
experiment:
  name: "hybrid_search_ablation"
  seed: 42

model:
  embedding: "sentence-transformers/all-mpnet-base-v2"
  reranker: "cross-encoder/ms-marco-MiniLM-L-12-v2"

search:
  type: "hybrid"
  alpha: 0.5  # Dense/sparse fusion weight
  top_k: 100
  rerank_top_n: 10

dataset:
  name: "msmarco-passage"
  split: "dev"
  sample_size: 1000

metrics:
  - "recall@10"
  - "mrr@10"
  - "ndcg@10"
```

**Run Experiment:**

```bash
# Single experiment
python experiments/run.py --config experiments/config.yaml

# Ablation study (vary alpha)
python experiments/run_ablation.py \
  --param search.alpha \
  --values 0.0,0.25,0.5,0.75,1.0

# Results saved to experiments/results/
```

**Reproduce Published Results:**

```bash
# Reproduce paper results
cd experiments/papers/rae_arxiv_2025

# Download exact model checkpoints
python download_checkpoints.py

# Run experiments (matches paper methodology)
bash run_all_experiments.sh

# Generate figures and tables
python generate_paper_figures.py
```

## 🧪 Research Use Cases

### Cognitive Architecture Research

**Simulating Human Memory:**

RAE's multi-layer architecture mirrors human memory systems:

```
┌─────────────────────────────────────────┐
│  Working Memory (7±2 items, seconds)   │  ← Attention/active context
└─────────────────────────────────────────┘
            ↓ consolidation
┌─────────────────────────────────────────┐
│  Episodic Memory (events, minutes-days) │  ← Recent experiences
└─────────────────────────────────────────┘
            ↓ abstraction
┌─────────────────────────────────────────┐
│  Semantic Memory (knowledge, long-term) │  ← Conceptual knowledge
└─────────────────────────────────────────┘
            ↓ consolidation
┌─────────────────────────────────────────┐
│  Long-Term Memory (schemas, permanent)  │  ← Principles & patterns
└─────────────────────────────────────────┘
```

**Research Questions:**

1. How does consolidation timing affect memory quality?
2. What is the optimal working memory capacity?
3. How should decay rates differ across layers?
4. Can we model primacy/recency effects?

**Example Experiment:**

```python
# Compare consolidation strategies
strategies = ["fixed_time", "threshold_based", "entropy_based"]

for strategy in strategies:
    # Configure RAE
    config = {
        "reflection_mode": strategy,
        "threshold": 100 if strategy == "threshold_based" else None,
        "interval_hours": 24 if strategy == "fixed_time" else None
    }

    # Run simulation
    results = run_memory_simulation(
        num_experiences=10000,
        query_distribution="zipf",
        config=config
    )

    # Measure quality
    metrics = {
        "recall": results.recall_at_k(10),
        "consolidation_quality": results.rouge_score(),
        "storage_efficiency": results.compression_ratio()
    }
```

### Memory Consolidation Studies

**Research Goal:** Understand optimal consolidation mechanisms

**Hypothesis:** Entropy-based consolidation outperforms fixed-time intervals

**Methodology:**

```python
# Setup
import rae_memory_sdk as rae

# Condition 1: Fixed-time consolidation
client_fixed = rae.RAEClient(config={
    "reflection_trigger": "fixed_time",
    "reflection_interval_hours": 24
})

# Condition 2: Entropy-based consolidation
client_entropy = rae.RAEClient(config={
    "reflection_trigger": "entropy",
    "entropy_threshold": 0.7
})

# Simulate experiences
experiences = generate_experiences(n=1000, pattern="clustered")

for exp in experiences:
    client_fixed.memories.create(content=exp)
    client_entropy.memories.create(content=exp)

# Measure outcomes
results_fixed = evaluate_memory_quality(client_fixed)
results_entropy = evaluate_memory_quality(client_entropy)

# Statistical test
p_value = ttest_ind(results_fixed, results_entropy)
```

### Multi-Agent Research

**Research Goal:** Study memory sharing in multi-agent systems

**Scenarios:**

1. **Shared Memory:** All agents access same memory pool
2. **Isolated Memory:** Each agent has private memory
3. **Selective Sharing:** Agents share specific memories
4. **Hierarchical Memory:** Manager agents consolidate worker memories

**Implementation:**

```python
# Scenario: Selective sharing
agents = {
    "agent_1": rae.RAEClient(tenant="multi_agent", project="agent_1"),
    "agent_2": rae.RAEClient(tenant="multi_agent", project="agent_2"),
    "shared": rae.RAEClient(tenant="multi_agent", project="shared"),
}

# Agent 1 has private experience
agents["agent_1"].memories.create(content="Private observation")

# Agent 1 shares important finding
important_finding = "Discovered optimal strategy X"
agents["shared"].memories.create(
    content=important_finding,
    metadata={"shared_by": "agent_1", "importance": "high"}
)

# Agent 2 can access shared memory
shared_memories = agents["shared"].memories.list()
```

**Metrics:**

- Communication efficiency (bits shared vs. performance)
- Convergence speed (time to optimal solution)
- Memory redundancy (overlap in stored knowledge)
- Coordination overhead (sync cost)

### Entity Resolution Research

**Problem:** Identify when two entity mentions refer to same real-world entity

**Example:**
- "Apple Inc." = "Apple" = "AAPL" = "Apple Computer"
- "NYC" = "New York City" = "The Big Apple"

**RAE Approach:**

```python
# Entity resolution with RAE
from rae_memory_sdk import RAEClient

client = RAEClient()

# Create entities
entities = [
    {"name": "Apple Inc.", "type": "company", "founded": 1976},
    {"name": "Apple", "type": "company", "industry": "tech"},
    {"name": "AAPL", "type": "stock_ticker"},
]

for entity in entities:
    client.graph.create_entity(entity)

# RAE automatically detects likely duplicates
duplicates = client.graph.find_duplicate_entities(threshold=0.8)

# Researcher can analyze resolution quality
precision, recall = evaluate_entity_resolution(duplicates, ground_truth)
```

### Prompt Engineering Research

**Research Goal:** Systematic optimization of LLM prompts for memory operations

**Variables:**

1. Prompt structure (zero-shot, few-shot, chain-of-thought)
2. Context length (how many memories to include)
3. Context ordering (recency, relevance, random)
4. Instruction framing (imperative, question, completion)

**Experiment:**

```python
# Define prompt templates
templates = {
    "zero_shot": "Answer: {query}",
    "few_shot": "Examples:\n{examples}\n\nAnswer: {query}",
    "cot": "Let's think step by step:\n{query}",
}

# Vary context length
context_sizes = [0, 3, 5, 10, 20]

# Measure performance
results = []
for template_name, template in templates.items():
    for k in context_sizes:
        memories = client.memories.search(query, limit=k)
        context = "\n".join([m.content for m in memories])

        prompt = template.format(query=query, context=context)
        response = llm.generate(prompt)

        score = evaluate_answer(response, ground_truth)
        results.append({
            "template": template_name,
            "context_size": k,
            "score": score
        })
```

## 📖 Academic Publications & Papers

### Citing RAE

**BibTeX:**

```bibtex
@software{rae_agentic_memory_2025,
  title = {RAE: Reflective Agentic-memory Engine},
  author = {Dreamsoft Pro Team},
  year = {2025},
  version = {1.0.0},
  url = {https://github.com/dreamsoft-pro/RAE-agentic-memory},
  note = {Multi-layer memory architecture with autonomous consolidation}
}
```

**APA:**
```
Dreamsoft Pro Team. (2025). RAE: Reflective Agentic-memory Engine (Version 1.0.0) [Computer software]. https://github.com/dreamsoft-pro/RAE-agentic-memory
```

### Published Research Using RAE

**Coming soon:** We'll maintain a list of academic papers that use RAE.

To add your paper:
1. Submit PR to `docs/research/publications.md`
2. Include: Title, authors, venue, year, DOI, brief description

### Research Datasets

**RAE Research Datasets:**

| Dataset | Size | Task | Download |
|---------|------|------|----------|
| **RAE-MemRecall** | 10k queries | Memory retrieval | [Link](#) |
| **RAE-Consolidation** | 50k experiences | Reflection quality | [Link](#) |
| **RAE-MultiAgent** | 100 episodes | Collaborative tasks | [Link](#) |
| **RAE-Temporal** | 20k events | Temporal reasoning | [Link](#) |

## 🛠️ Research Tools & APIs

### Python Research SDK

**Install:**

```bash
pip install rae-research-sdk
```

**Usage:**

```python
from rae_research import Experiment, Metrics

# Setup experiment
exp = Experiment(
    name="hybrid_search_study",
    config="configs/baseline.yaml",
    seed=42
)

# Run trials
results = exp.run(n_trials=100)

# Analyze
metrics = Metrics(results)
print(f"Mean NDCG@10: {metrics.mean('ndcg@10')} ± {metrics.std('ndcg@10')}")

# Statistical tests
p_value = metrics.compare(baseline_results, method="ttest")

# Visualize
metrics.plot_distribution("ndcg@10", save="figures/ndcg_dist.pdf")
```

### Jupyter Notebooks

**Interactive Research:**

```bash
# Clone research notebooks
git clone https://github.com/dreamsoft-pro/rae-research-notebooks.git
cd rae-research-notebooks

# Install dependencies
pip install -r requirements.txt

# Launch Jupyter
jupyter lab

# Open notebooks/
# - 01_memory_encoding.ipynb
# - 02_hybrid_search.ipynb
# - 03_consolidation.ipynb
# - 04_multi_agent.ipynb
```

### Data Export for Analysis

**Data Recovery:**
If you encounter missing data after an update, please refer to the [Data Recovery Guide](../developers/INDEX.md#data-recovery--maintenance) for instructions on normalizing memory layers.

**Export memories for external analysis:**

```python
# Export to pandas DataFrame
import pandas as pd

memories = client.memories.list()
df = pd.DataFrame([
    {
        "id": m.id,
        "content": m.content,
        "embedding": m.embedding,
        "created_at": m.created_at,
        **m.metadata
    }
    for m in memories
])

# Export embeddings for t-SNE/UMAP
embeddings = np.array([m.embedding for m in memories])
np.save("embeddings.npy", embeddings)

# Export graph for NetworkX
import networkx as nx

G = client.graph.export_networkx()
nx.write_gexf(G, "knowledge_graph.gexf")
```

### Reproducibility Checklist

**For publishing research using RAE:**

- [ ] Record RAE version: `client.version()`
- [ ] Save configuration: `config.yaml`
- [ ] Set random seed: `seed=42`
- [ ] Document dataset splits
- [ ] Include model checkpoints
- [ ] Report hardware specs (CPU/GPU/RAM)
- [ ] Measure and report runtime
- [ ] Provide statistical significance tests
- [ ] Share code on GitHub/GitLab
- [ ] Make results reproducible: `experiments/` directory

## 🎓 Learning Resources for Researchers

### Theoretical Background

**Recommended Reading:**

1. **Memory Systems:**
   - Tulving, E. (1985). "Elements of Episodic Memory"
   - Atkinson, R. & Shiffrin, R. (1968). "Human Memory: A Proposed System"

2. **Information Retrieval:**
   - Manning, C. et al. (2008). "Introduction to Information Retrieval"
   - Zobel, J. & Moffat, A. (2006). "Inverted files for text search engines"

3. **Knowledge Graphs:**
   - Hogan, A. et al. (2021). "Knowledge Graphs"
   - Fensel, D. et al. (2020). "Knowledge Graphs: Methodology, Tools and Selected Use Cases"

4. **LLM & Embeddings:**
   - Reimers, N. & Gurevych, I. (2019). "Sentence-BERT"
   - Gao, L. et al. (2021). "SimCSE"

### Tutorials & Workshops

**Coming soon:**
- "Building Cognitive Architectures with RAE" (workshop)
- "Benchmarking Memory Systems" (tutorial)
- "Multi-Agent Research with RAE" (workshop)

### Research Community

**Join the Research Community:**

- **Mailing List:** research@rae-memory.ai
- **Discord Channel:** #research
- **Monthly Research Calls:** First Friday of each month
- **GitHub Discussions:** [Research Topics](https://github.com/dreamsoft-pro/RAE-agentic-memory/discussions/categories/research)

**Collaborations:**

We welcome research collaborations! Contact: research@rae-memory.ai

## 📊 Research Dashboards

### Performance Monitoring

**Real-time Metrics:**

```python
# Research metrics endpoint
GET /api/v1/research/metrics

{
  "embeddings": {
    "total_count": 1_000_000,
    "avg_dimension": 768,
    "total_size_gb": 3.2
  },
  "retrieval": {
    "avg_latency_ms": 45,
    "p95_latency_ms": 120,
    "p99_latency_ms": 250
  },
  "consolidation": {
    "total_reflections": 5_432,
    "avg_quality_score": 0.87,
    "compression_ratio": 12.3
  },
  "graph": {
    "total_entities": 123_456,
    "total_edges": 456_789,
    "avg_degree": 3.7
  }
}
```

### Experiment Tracking

**Integration with MLflow:**

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("rae_hybrid_search")

with mlflow.start_run():
    # Log parameters
    mlflow.log_param("embedding_model", "all-mpnet-base-v2")
    mlflow.log_param("alpha", 0.5)

    # Run experiment
    results = run_search_experiment(config)

    # Log metrics
    mlflow.log_metric("ndcg@10", results["ndcg@10"])
    mlflow.log_metric("recall@10", results["recall@10"])

    # Log artifacts
    mlflow.log_artifact("results.json")
```

## 🔗 Related Research Projects

**RAE Ecosystem:**

- **RAE Benchmarks:** Standard evaluation suite
- **RAE Research SDK:** Tools for researchers
- **RAE Notebooks:** Jupyter tutorials and examples
- **RAE Papers:** Research publications using RAE

## 🗺️ Research Roadmap

**Current Version:** 1.0.0

**Q1 2025:**
- ✅ Multi-layer memory architecture
- ✅ Hybrid search (vector + BM25)
- ✅ Autonomous reflection engine
- 🔄 Research SDK v1.0
- 🔄 Benchmark suite release

**Q2 2025:**
- Multi-modal embeddings (text + images)
- Advanced entity resolution
- Federated learning for memory models
- Continual learning experiments

**Q3 2025:**
- Neuro-symbolic reasoning
- Causal memory graphs
- Zero-shot memory transfer
- Memory efficiency optimizations

**See [Research Roadmap](../../reference/research/roadmap.md) for details.**

---

**Have research questions?** Email: research@rae-memory.ai

**Want to collaborate?** Reach out: partnerships@rae-memory.ai

**Interested in research internships?** Check: [rae-memory.ai/careers](https://rae-memory.ai/careers)

**Last Updated:** 2025-12-06
