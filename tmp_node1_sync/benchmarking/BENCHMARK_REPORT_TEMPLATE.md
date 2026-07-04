# RAE Benchmark Report Template

This template provides a standardized format for reporting RAE benchmark results. Use this for academic papers, technical reports, or internal documentation.

---

# RAE Benchmark Report: [BENCHMARK_NAME]

**Description:** [Brief description of what this benchmark evaluates]

**Executed:** [ISO 8601 timestamp]
**Version:** [RAE version being tested]
**Hardware:** [CPU, RAM, OS details]

---

## 1. Executive Summary

**Overall Quality Score:** [0.0-1.0] [✅/⚠️/❌]
**Average Query Latency:** [X]ms [✅/⚠️/❌]
**Test Duration:** [X] seconds

**Key Findings:**
- [Finding 1]
- [Finding 2]
- [Finding 3]

**Recommendation:** [Deploy / Needs Improvement / Do Not Deploy]

---

## 2. Dataset Overview

| Property | Value |
|----------|-------|
| **Benchmark Set** | [e.g., academic_extended] |
| **Number of Memories** | [X] |
| **Number of Queries** | [X] |
| **Data Domains** | [e.g., CS, Physics, Biology] |
| **Query Difficulty** | [Easy: X, Medium: Y, Hard: Z] |

**Dataset Characteristics:**
- Memory size range: [min - max] characters
- Query complexity: [simple facts / semantic matching / inference]
- Noise level: [low / medium / high]

---

## 3. Quality Metrics

### 3.1 Information Retrieval Metrics

| Metric | Score | Threshold | Status | Notes |
|--------|-------|-----------|--------|-------|
| **MRR** (Mean Reciprocal Rank) | [0.XXX] | > 0.70 | [✅/⚠️/❌] | Average rank of first relevant result |
| **Hit Rate @3** | [0.XXX] | > 0.65 | [✅/⚠️/❌] | % queries with hit in top 3 |
| **Hit Rate @5** | [0.XXX] | > 0.75 | [✅/⚠️/❌] | % queries with hit in top 5 |
| **Hit Rate @10** | [0.XXX] | > 0.85 | [✅/⚠️/❌] | % queries with hit in top 10 |
| **Precision @5** | [0.XXX] | > 0.60 | [✅/⚠️/❌] | Accuracy of top 5 results |
| **Recall @5** | [0.XXX] | > 0.70 | [✅/⚠️/❌] | Coverage of relevant docs |
| **Overall Quality** | [0.XXX] | > 0.75 | [✅/⚠️/❌] | Weighted composite score |

**Interpretation:**
- [Interpretation of MRR score]
- [Interpretation of Hit Rate trends]
- [Interpretation of Precision/Recall balance]

### 3.2 Performance by Query Difficulty

| Difficulty | Count | MRR | Hit Rate @5 | Avg Latency |
|------------|-------|-----|-------------|-------------|
| Easy | [X] | [0.XXX] | [0.XXX] | [XX]ms |
| Medium | [X] | [0.XXX] | [0.XXX] | [XX]ms |
| Hard | [X] | [0.XXX] | [0.XXX] | [XX]ms |
| Very Hard | [X] | [0.XXX] | [0.XXX] | [XX]ms |

**Observations:**
- [Pattern analysis across difficulty levels]
- [Notable failures or successes]

---

## 4. Performance Metrics

### 4.1 Latency Analysis

| Metric | Value | Threshold | Status | Notes |
|--------|-------|-----------|--------|-------|
| **Average Insert Time** | [XX.XX]ms | < 150ms | [✅/⚠️/❌] | Per memory insertion |
| **Average Query Time** | [XX.XX]ms | < 100ms | [✅/⚠️/❌] | Mean latency |
| **P50 Query Time** | [XX.XX]ms | < 80ms | [✅/⚠️/❌] | Median latency |
| **P95 Query Time** | [XX.XX]ms | < 200ms | [✅/⚠️/❌] | 95th percentile |
| **P99 Query Time** | [XX.XX]ms | < 300ms | [✅/⚠️/❌] | 99th percentile |
| **Min Query Time** | [XX.XX]ms | - | ℹ️ | Fastest query |
| **Max Query Time** | [XX.XX]ms | - | ℹ️ | Slowest query |

### 4.2 Throughput

| Metric | Value |
|--------|-------|
| **Memories Inserted/sec** | [X.XX] |
| **Queries Processed/sec** | [X.XX] |
| **Total Benchmark Time** | [X.XX] seconds |

### 4.3 Latency Distribution

```
Query Latency Distribution:
0-50ms:   ████████████████████ 45%
50-100ms: ███████████████ 30%
100-200ms: ████████ 20%
200ms+:   ██ 5%
```

---

## 5. System Configuration

### 5.1 RAE Configuration

| Component | Configuration |
|-----------|---------------|
| **Embedding Model** | [e.g., sentence-transformers/all-MiniLM-L6-v2] |
| **Vector Dimension** | [e.g., 384] |
| **Top K** | [e.g., 5] |
| **Min Relevance Score** | [e.g., 0.3] |
| **Reranking** | [Enabled / Disabled] |
| **Reflection Engine** | [Enabled / Disabled] |
| **GraphRAG** | [Enabled / Disabled] |

### 5.2 Infrastructure

| Component | Specification |
|-----------|---------------|
| **CPU** | [e.g., Intel i7-9700K @ 3.6GHz] |
| **RAM** | [e.g., 16GB DDR4] |
| **Storage** | [e.g., NVMe SSD] |
| **Database** | [e.g., PostgreSQL 15.3] |
| **Vector Store** | [e.g., pgvector] |
| **OS** | [e.g., Ubuntu 22.04 LTS] |

---

## 6. Detailed Analysis

### 6.1 Quality Breakdown by Category

For benchmarks with categorized queries (e.g., industrial_small):

| Category | Count | MRR | Hit@5 | Notes |
|----------|-------|-----|-------|-------|
| Factual Recall | [X] | [0.XXX] | [0.XXX] | [Notes] |
| Semantic Matching | [X] | [0.XXX] | [0.XXX] | [Notes] |
| Inference | [X] | [0.XXX] | [0.XXX] | [Notes] |
| Multi-hop | [X] | [0.XXX] | [0.XXX] | [Notes] |

### 6.2 Notable Query Results

**Best Performing Queries:**
1. Query: "[Query text]"
   - Expected: [ID], Retrieved: [ID] at rank [X]
   - Latency: [XX]ms
   - Explanation: [Why it performed well]

2. [Additional examples]

**Worst Performing Queries:**
1. Query: "[Query text]"
   - Expected: [ID], Retrieved: [ID] at rank [X or "not found"]
   - Latency: [XX]ms
   - Explanation: [Root cause analysis]

2. [Additional examples]

---

## 7. Observations & Insights

### 7.1 Strengths

- ✅ [Strength 1: e.g., "Excellent performance on factual queries"]
- ✅ [Strength 2: e.g., "Very fast query latency (avg 45ms)"]
- ✅ [Strength 3: e.g., "High hit rate for top 5 results"]

### 7.2 Weaknesses

- ❌ [Weakness 1: e.g., "Struggles with inference-based queries"]
- ❌ [Weakness 2: e.g., "P99 latency exceeds 300ms"]
- ❌ [Weakness 3: e.g., "Low recall on multi-domain queries"]

### 7.3 Unexpected Findings

- [Surprising result 1]
- [Surprising result 2]

---

## 8. Comparison with Previous Runs

*(Include this section if comparing with baseline)*

### 8.1 Quality Changes

| Metric | Previous | Current | Change | Status |
|--------|----------|---------|--------|--------|
| MRR | [0.XXX] | [0.XXX] | [+/- X.XX%] | [✅/❌] |
| Hit Rate @5 | [0.XXX] | [0.XXX] | [+/- X.XX%] | [✅/❌] |
| Overall Quality | [0.XXX] | [0.XXX] | [+/- X.XX%] | [✅/❌] |

### 8.2 Performance Changes

| Metric | Previous | Current | Change | Status |
|--------|----------|---------|--------|--------|
| Avg Query Time | [XX]ms | [XX]ms | [+/- XX%] | [✅/❌] |
| P95 Latency | [XX]ms | [XX]ms | [+/- XX%] | [✅/❌] |

**Summary:** [Overall trend - improvement/regression/stable]

---

## 9. Recommendations

### 9.1 Immediate Actions

1. **[Priority: High/Medium/Low]** [Action item 1]
   - Rationale: [Why this is important]
   - Expected Impact: [Estimated improvement]

2. [Additional actions]

### 9.2 Future Improvements

1. [Long-term improvement 1]
2. [Long-term improvement 2]

### 9.3 Configuration Tuning

Suggested configuration changes:

```yaml
# Recommended settings
top_k: [X]
min_relevance_score: [X.XX]
enable_reranking: [true/false]
enable_reflection: [true/false]
```

Rationale: [Why these changes]

---

## 10. Reproducibility

### 10.1 How to Reproduce

```bash
# Step 1: Setup environment
export POSTGRES_HOST=localhost
export POSTGRES_DB=rae_memory

# Step 2: Run benchmark
python benchmarking/scripts/run_benchmark.py --set [benchmark_file].yaml

# Step 3: View results
cat benchmarking/results/[benchmark_name]_*.md
```

### 10.2 Data & Code

- **Benchmark Set:** `benchmarking/sets/[filename].yaml`
- **RAE Version:** [commit hash or version]
- **Random Seed:** [if applicable]
- **Dataset Checksum:** [SHA256 hash of YAML file]

---

## 11. Conclusion

**Summary:** [1-2 sentence summary of results]

**Assessment:** [Pass / Conditional Pass / Fail]

**Next Steps:**
1. [Next step 1]
2. [Next step 2]

---

## Appendix A: Detailed Query Results

*(Optional: Include full table of all queries and results)*

| Query ID | Query Text | Expected | Retrieved Rank | Latency | Hit |
|----------|------------|----------|----------------|---------|-----|
| 1 | [text] | [ID] | [X] | [XX]ms | [✅/❌] |
| ... | ... | ... | ... | ... | ... |

---

## Appendix B: Raw Data

**JSON Results File:** `[filename].json`

**Key Statistics:**
```json
{
  "metrics": {
    "mrr": 0.XXXX,
    "hit_rate": {"@5": 0.XXXX},
    "overall_quality_score": 0.XXXX
  }
}
```

---

*Generated by RAE Benchmarking Suite v1.0*
*Report Template Version: 1.0*
*Date: [YYYY-MM-DD]*

---

## Using This Template

### For Quick Reports
Fill in sections 1-4 for a concise report.

### For Academic Papers
Include all sections with detailed analysis (sections 5-8).

### For Internal Use
Focus on sections 3, 4, and 7 (metrics and insights).

### For Regression Testing
Emphasize section 8 (comparisons with previous runs).

---

## Template Checklist

- [ ] All [PLACEHOLDER] values replaced
- [ ] Metrics meet/exceed thresholds marked correctly (✅/⚠️/❌)
- [ ] Performance numbers include proper units (ms, %, etc.)
- [ ] At least 3 observations in section 7
- [ ] Recommendations are actionable and specific
- [ ] Reproducibility section is complete
- [ ] Conclusion includes clear next steps
