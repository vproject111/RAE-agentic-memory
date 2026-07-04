# LaTeX Description for Academic Papers

This document contains LaTeX-formatted descriptions of RAE suitable for academic papers, theses, and technical reports.

---

## Short Description (for Abstract/Introduction)

```latex
RAE (Reflective Agentic-memory Engine) is an open-source memory system for AI agents that implements a four-layer hierarchical architecture inspired by cognitive science. It combines episodic memory for recent events, semantic memory with vector embeddings, knowledge graphs for structured relations, and reflective memory for long-term consolidation. The system includes a reflection engine modeled as a Markov Decision Process that optimizes memory quality under cost constraints.
```

---

## Full Technical Description

```latex
\section{RAE: Reflective Agentic-memory Engine}

RAE is an open-source memory architecture designed to enable long-term, interpretable and auditable memory for AI agents. It implements a four-layer hierarchical model inspired by cognitive systems:

\begin{itemize}
\item \textbf{Episodic Memory:} short-term contextual traces with temporal ordering and recency bias.
\item \textbf{Semantic Memory:} embedding-based similarity retrieval with hybrid search combining dense vectors and BM25 keyword matching.
\item \textbf{Graph Memory:} entity–relation graph constructed from extracted triples with support for traversal and community detection.
\item \textbf{Reflective Memory:} long-term consolidation through summarization, pruning and reinforcement based on access patterns.
\end{itemize}

The reflection process is modeled as a Markov Decision Process optimizing memory quality under cost constraints. The system maintains a state representation of current memory configuration and selects actions (consolidate, prune, reinforce) to maximize a reward function that balances retrieval accuracy, memory coherence, and operational cost.

RAE provides:
\begin{itemize}
\item a modular API for retrieval, reasoning and consolidation,
\item ISO 42001-compliant governance (risk assessment, provenance tracking, human oversight),
\item OpenTelemetry instrumentation for scientific measurement,
\item an A/B testing framework and reproducible benchmarks.
\end{itemize}

RAE aims to serve as a research platform for studying long-term memory, knowledge stability, and reasoning behavior in agentic systems.
```

---

## Mathematical Formulation

```latex
\subsection{Memory as a Markov Decision Process}

Let $\mathcal{M} = (S, A, P, R, \gamma)$ be the memory management MDP where:

\begin{itemize}
\item $S$ is the state space representing memory configurations, where each state $s \in S$ is characterized by:
  \begin{equation}
  s = (M_e, M_s, M_g, M_r, Q, C)
  \end{equation}
  with $M_e, M_s, M_g, M_r$ representing episodic, semantic, graph, and reflective memory states respectively, $Q$ the quality metric, and $C$ the cumulative cost.

\item $A$ is the action space containing memory operations:
  \begin{equation}
  A = \{\text{consolidate}, \text{prune}, \text{reinforce}, \text{summarize}, \text{noop}\}
  \end{equation}

\item $P: S \times A \rightarrow \Delta(S)$ is the state transition function.

\item $R: S \times A \rightarrow \mathbb{R}$ is the reward function:
  \begin{equation}
  R(s, a) = \alpha \cdot Q(s') - \beta \cdot C(a) - \lambda \cdot |M(s')|
  \end{equation}
  where $Q(s')$ measures retrieval quality, $C(a)$ is the operational cost, $|M(s')|$ is the memory size, and $\alpha, \beta, \lambda$ are hyperparameters.

\item $\gamma \in [0,1]$ is the discount factor for future rewards.
\end{itemize}

The optimal policy $\pi^*: S \rightarrow A$ is learned (or heuristically defined) to maximize expected cumulative reward:
\begin{equation}
\pi^* = \arg\max_{\pi} \mathbb{E}\left[\sum_{t=0}^{\infty} \gamma^t R(s_t, \pi(s_t))\right]
\end{equation}
```

---

## Retrieval Process

```latex
\subsection{Hybrid Retrieval in Semantic Memory}

Given a query $q$, the retrieval process combines multiple strategies:

\textbf{Dense Vector Retrieval:}
\begin{equation}
\text{sim}_{\text{vec}}(q, m_i) = \frac{e_q \cdot e_{m_i}}{\|e_q\| \|e_{m_i}\|}
\end{equation}
where $e_q$ and $e_{m_i}$ are embedding vectors for query and memory $m_i$.

\textbf{Sparse Keyword Retrieval (BM25):}
\begin{equation}
\text{score}_{\text{BM25}}(q, m_i) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t, m_i) \cdot (k_1 + 1)}{f(t, m_i) + k_1 \cdot (1 - b + b \cdot \frac{|m_i|}{\text{avgdl}})}
\end{equation}

\textbf{Hybrid Fusion:}
\begin{equation}
\text{score}_{\text{hybrid}}(q, m_i) = w_v \cdot \text{sim}_{\text{vec}}(q, m_i) + w_k \cdot \text{score}_{\text{BM25}}(q, m_i)
\end{equation}
with learned or tuned weights $w_v, w_k$.

\textbf{Reranking (Optional):}
A cross-encoder model $f_{\text{rerank}}$ provides fine-grained relevance:
\begin{equation}
\text{score}_{\text{final}}(q, m_i) = f_{\text{rerank}}(q, m_i)
\end{equation}
```

---

## Graph Operator

```latex
\subsection{Knowledge Graph Operations}

The knowledge graph $G = (V, E)$ consists of:
\begin{itemize}
\item Vertices $V$: entities extracted from memories
\item Edges $E \subseteq V \times R \times V$: relations with types $R$
\end{itemize}

\textbf{Graph Traversal:}
Given a starting entity $v_0$ and maximum depth $d$, retrieve subgraph:
\begin{equation}
G_{sub}(v_0, d) = \{v \in V : \text{dist}(v_0, v) \leq d\}
\end{equation}

\textbf{Community Detection:}
Apply Louvain algorithm or label propagation to identify clusters:
\begin{equation}
C = \{C_1, C_2, \ldots, C_k\} \text{ where } \bigcup_{i=1}^k C_i = V
\end{equation}

\textbf{Centrality Metrics:}
Importance of entity $v$ measured by degree, betweenness, or PageRank:
\begin{equation}
\text{PR}(v) = \frac{1-d}{|V|} + d \sum_{u \in \text{incoming}(v)} \frac{\text{PR}(u)}{|\text{outgoing}(u)|}
\end{equation}
```

---

## Reflection Engine

```latex
\subsection{Memory Consolidation Strategy}

The consolidation process transfers knowledge from lower to upper layers:

\textbf{Episodic $\rightarrow$ Semantic:}
Frequently accessed episodic memories with high importance scores are converted to semantic memories:
\begin{equation}
\text{promote}(m) \Leftrightarrow \text{access\_count}(m) > \theta_a \land \text{importance}(m) > \theta_i
\end{equation}

\textbf{Semantic $\rightarrow$ Graph:}
Entity and relation extraction from semantic memories:
\begin{equation}
(e_s, r, e_o) = \text{extract}(m) \implies \text{add\_edge}(G, e_s, r, e_o)
\end{equation}

\textbf{Multiple Memories $\rightarrow$ Reflective:}
Pattern detection and summarization across related memories:
\begin{equation}
m_{\text{reflect}} = \text{summarize}(\{m_i : \text{sim}(m_i, m_j) > \theta_s\})
\end{equation}
```

---

## Governance Layer

```latex
\subsection{ISO 42001 Compliance}

RAE implements governance controls required by ISO 42001:

\begin{itemize}
\item \textbf{Risk Assessment:} Automated risk scoring for memory operations based on content sensitivity and operational impact.

\item \textbf{Provenance Tracking:} Complete lineage for all memories:
  \begin{equation}
  \text{provenance}(m) = (t_{\text{created}}, \text{source}, \text{transformations}, \text{dependencies})
  \end{equation}

\item \textbf{Human-in-the-Loop (HITL):} Approval workflows for high-risk operations:
  \begin{equation}
  \text{execute}(a) \Leftrightarrow (\text{risk}(a) < \theta_{\text{risk}}) \lor \text{approved}(a)
  \end{equation}

\item \textbf{Circuit Breakers:} Safety constraints preventing harmful operations:
  \begin{equation}
  \text{block}(a) \Leftrightarrow \text{violates}(a, \text{policies})
  \end{equation}

\item \textbf{Audit Logs:} Comprehensive logging of all operations for compliance and forensics.
\end{itemize}
```

---

## Benchmarking Metrics

```latex
\subsection{Evaluation Metrics}

RAE evaluation uses standard information retrieval metrics:

\textbf{Hit Rate@K:}
\begin{equation}
\text{HR@K} = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{1}[\text{relevant}(q) \cap \text{top\_k}(q) \neq \emptyset]
\end{equation}

\textbf{Mean Reciprocal Rank (MRR):}
\begin{equation}
\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_{\text{first\_relevant}}(q)}
\end{equation}

\textbf{Precision@K and Recall@K:}
\begin{equation}
\text{P@K} = \frac{|\text{relevant}(q) \cap \text{top\_k}(q)|}{K}
\end{equation}
\begin{equation}
\text{R@K} = \frac{|\text{relevant}(q) \cap \text{top\_k}(q)|}{|\text{relevant}(q)|}
\end{equation}

\textbf{Latency:}
Average and percentile latencies:
\begin{equation}
\text{P95\_latency} = \text{percentile}(\{\text{latency}(q) : q \in Q\}, 0.95)
\end{equation}
```

---

## BibTeX Citation

```latex
@software{rae2025,
  title = {RAE: Reflective Agentic-memory Engine},
  author = {Leśniowski, Grzegorz},
  year = {2025},
  url = {https://github.com/dreamsoft-pro/RAE-agentic-memory},
  version = {2.2.0},
  note = {Open-source memory system for AI agents with 4-layer architecture and reflection engine}
}
```

---

## Usage in Papers

### In Abstract
"We evaluate our approach using RAE (Reflective Agentic-memory Engine) \cite{rae2025}, an open-source memory system that implements a four-layer hierarchical architecture..."

### In Related Work
"Recent work on agentic memory systems includes RAE \cite{rae2025}, which combines episodic, semantic, graph, and reflective memory layers with a reflection engine modeled as an MDP."

### In Experimental Setup
"For reproducibility, we use RAE version 2.2.0 \cite{rae2025} deployed via Docker Compose with the following configuration: top\_k=5, embedding model=text-embedding-3-small, reranker=bge-reranker-base."

---

## Contact for Academic Collaboration

For research collaborations, custom benchmarks, or questions about RAE:

- **Repository:** https://github.com/dreamsoft-pro/RAE-agentic-memory
- **Issues:** https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
- **Discussions:** https://github.com/dreamsoft-pro/RAE-agentic-memory/discussions
