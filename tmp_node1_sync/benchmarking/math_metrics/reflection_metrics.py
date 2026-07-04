"""
Reflection Metrics - Quality and Performance of Reflection Operations

These metrics analyze the reflection system's performance and quality:
- Reflection Latency (RL): Time taken for reflection operations
- Insight Precision (IP): Quality/accuracy of generated insights
- Insight Stability (IS): Consistency of insights over time
- Critical Event Detection Score (CEDS): Ability to detect important events
- Contradiction Avoidance Score (CAS): Logical consistency of insights

The reflection system in RAE generates insights from memory clusters,
learns from successes/failures, and produces hierarchical meta-insights.
These metrics help evaluate how well the reflection engine performs.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from numpy.typing import NDArray

from .base import MathMetricBase, cosine_similarity, jaccard_similarity

# ============================================================================
# Helper Functions
# ============================================================================


def extract_key_terms(text: str, min_length: int = 3) -> Set[str]:
    """
    Extract key terms from text for comparison.

    Simple tokenization that extracts lowercase words.
    For production use, consider using NLP libraries like spaCy or NLTK.

    Args:
        text: Input text to tokenize
        min_length: Minimum word length to include

    Returns:
        Set of lowercase key terms
    """
    if not text:
        return set()

    # Simple word extraction (alphanumeric words only)
    words = []
    current_word = []

    for char in text.lower():
        if char.isalnum():
            current_word.append(char)
        else:
            if current_word:
                word = "".join(current_word)
                if len(word) >= min_length:
                    words.append(word)
                current_word = []

    # Don't forget the last word
    if current_word:
        word = "".join(current_word)
        if len(word) >= min_length:
            words.append(word)

    return set(words)


def calculate_f1_score(
    precision: float,
    recall: float,
) -> float:
    """
    Calculate F1 score from precision and recall.

    Formula: F1 = 2 * (precision * recall) / (precision + recall)

    Args:
        precision: Precision value (0.0 to 1.0)
        recall: Recall value (0.0 to 1.0)

    Returns:
        F1 score (0.0 to 1.0)
    """
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def detect_contradiction(
    insight_a: str,
    insight_b: str,
    embedding_a: Optional[NDArray[np.float32]] = None,
    embedding_b: Optional[NDArray[np.float32]] = None,
    contradiction_threshold: float = 0.3,
) -> Tuple[bool, float]:
    """
    Detect if two insights contradict each other.

    Uses multiple heuristics:
    1. Embedding-based: Low similarity with negation patterns
    2. Term-based: Presence of opposing terms

    Note: This is a simplified heuristic approach. For production use,
    consider using NLI (Natural Language Inference) models.

    Args:
        insight_a: First insight text
        insight_b: Second insight text
        embedding_a: Optional embedding for first insight
        embedding_b: Optional embedding for second insight
        contradiction_threshold: Similarity threshold below which
                                 contradictions are detected

    Returns:
        Tuple of (is_contradiction, contradiction_score)
        where score is 0.0 (no contradiction) to 1.0 (strong contradiction)
    """
    # Negation patterns that might indicate contradiction
    negation_patterns = [
        ("always", "never"),
        ("should", "should not"),
        ("must", "must not"),
        ("increase", "decrease"),
        ("better", "worse"),
        ("success", "failure"),
        ("enable", "disable"),
        ("true", "false"),
        ("correct", "incorrect"),
        ("valid", "invalid"),
    ]

    # Extract terms
    terms_a = extract_key_terms(insight_a)
    terms_b = extract_key_terms(insight_b)

    contradiction_score = 0.0

    # Check for negation pattern presence
    for pos, neg in negation_patterns:
        if (pos in terms_a and neg in terms_b) or (neg in terms_a and pos in terms_b):
            contradiction_score += 0.3

    # If embeddings are provided, use semantic similarity
    if embedding_a is not None and embedding_b is not None:
        similarity = cosine_similarity(embedding_a, embedding_b)

        # High similarity with negation patterns suggests contradiction
        # Low similarity alone doesn't necessarily mean contradiction
        if contradiction_score > 0 and similarity > 0.5:
            # Similar topics but opposing terms = likely contradiction
            contradiction_score += 0.4
        elif similarity < contradiction_threshold and contradiction_score > 0:
            # Different topics with negation patterns
            contradiction_score += 0.2

    # Normalize to 0-1 range
    contradiction_score = min(1.0, contradiction_score)

    is_contradiction = contradiction_score > 0.5

    return is_contradiction, contradiction_score


# ============================================================================
# Reflection Metrics
# ============================================================================


class ReflectionLatency(MathMetricBase):
    """
    Reflection Latency (RL)

    Measures the time taken for reflection operations in milliseconds.

    This metric tracks the performance of the reflection pipeline,
    including:
    - Memory clustering time
    - LLM generation time
    - Embedding generation time
    - Database storage time

    Formula: RL = average(reflection_times)

    Lower latency is better for real-time applications.
    Higher latency may indicate complex clustering or slow LLM responses.

    Range: 0ms to unbounded (typical: 50-500ms for simple reflections,
           1000-5000ms for complex clustering + generation)

    Example:
        >>> latency = ReflectionLatency()
        >>> result = latency.calculate(
        ...     reflection_times=[120.5, 150.2, 95.8, 200.1, 180.0]
        ... )
        >>> print(f"Average latency: {result:.1f}ms")
        Average latency: 149.3ms
    """

    def __init__(self):
        super().__init__(
            name="reflection_latency",
            description="Average time taken for reflection operations (milliseconds)",
        )

    def calculate(
        self,
        reflection_times: List[float],
        percentile: Optional[float] = None,
    ) -> float:
        """
        Calculate average reflection latency from execution traces.

        Args:
            reflection_times: List of reflection execution times in milliseconds.
                             Each entry represents one reflection operation.
            percentile: Optional percentile to calculate (e.g., 95 for p95).
                       If None, returns the mean.

        Returns:
            Average (or percentile) latency in milliseconds.
            Returns 0.0 if no times provided.
        """
        if not reflection_times or len(reflection_times) == 0:
            self._last_value = 0.0
            self._last_metadata = {
                "num_reflections": 0,
                "reason": "No reflection times provided",
            }
            return 0.0

        times_array = np.array(reflection_times, dtype=np.float64)

        # Calculate statistics
        mean_latency = float(np.mean(times_array))
        min_latency = float(np.min(times_array))
        max_latency = float(np.max(times_array))
        std_latency = float(np.std(times_array))
        p50_latency = float(np.percentile(times_array, 50))
        p95_latency = float(np.percentile(times_array, 95))
        p99_latency = float(np.percentile(times_array, 99))

        # Return requested metric
        if percentile is not None:
            result = float(np.percentile(times_array, percentile))
        else:
            result = mean_latency

        self._last_value = result
        self._last_metadata = {
            "num_reflections": len(reflection_times),
            "mean_ms": mean_latency,
            "min_ms": min_latency,
            "max_ms": max_latency,
            "std_ms": std_latency,
            "p50_ms": p50_latency,
            "p95_ms": p95_latency,
            "p99_ms": p99_latency,
            "total_time_ms": float(np.sum(times_array)),
        }

        return result


class InsightPrecision(MathMetricBase):
    """
    Insight Precision (IP)

    Measures the quality and accuracy of generated insights by comparing
    them against expected patterns or ground truth.

    This metric evaluates how well the reflection engine produces
    insights that match:
    1. Expected semantic content (via embedding similarity)
    2. Expected key terms/concepts (via term overlap)
    3. Manual quality scores (if available)

    Formula:
        IP = weighted_average(
            semantic_similarity_score,
            term_overlap_score,
            manual_quality_score
        )

    Where weights can be configured based on evaluation priorities.

    Range: 0.0 (poor quality, no match) to 1.0 (perfect match)
    Typical good value: > 0.7

    Example:
        >>> precision = InsightPrecision()
        >>> result = precision.calculate(
        ...     generated_insights=["Use caching to improve performance"],
        ...     expected_insights=["Implement caching for better speed"],
        ...     insight_embeddings=generated_embeddings,
        ...     expected_embeddings=expected_embeddings,
        ... )
        >>> print(f"Insight precision: {result:.2f}")
        Insight precision: 0.85
    """

    def __init__(self):
        super().__init__(
            name="insight_precision",
            description="Quality/accuracy of generated insights",
        )

    def calculate(
        self,
        generated_insights: List[str],
        expected_insights: Optional[List[str]] = None,
        insight_embeddings: Optional[List[NDArray[np.float32]]] = None,
        expected_embeddings: Optional[List[NDArray[np.float32]]] = None,
        manual_scores: Optional[List[float]] = None,
        semantic_weight: float = 0.5,
        term_weight: float = 0.3,
        manual_weight: float = 0.2,
    ) -> float:
        """
        Calculate insight precision using multiple quality signals.

        Args:
            generated_insights: List of generated insight texts
            expected_insights: Optional list of expected/ideal insight texts
            insight_embeddings: Optional embeddings for generated insights
            expected_embeddings: Optional embeddings for expected insights
            manual_scores: Optional list of manual quality scores (0-1)
            semantic_weight: Weight for semantic similarity component
            term_weight: Weight for term overlap component
            manual_weight: Weight for manual scores component

        Returns:
            Precision score (0.0 to 1.0)
        """
        if not generated_insights:
            self._last_value = 0.0
            self._last_metadata = {
                "num_insights": 0,
                "reason": "No generated insights provided",
            }
            return 0.0

        num_insights = len(generated_insights)
        scores: Dict[str, List[float]] = {
            "semantic": [],
            "term": [],
            "manual": [],
        }

        # Calculate semantic similarity scores
        if (
            insight_embeddings is not None
            and expected_embeddings is not None
            and len(insight_embeddings) > 0
            and len(expected_embeddings) > 0
        ):
            for gen_emb in insight_embeddings:
                # Find best match among expected embeddings
                best_sim = 0.0
                for exp_emb in expected_embeddings:
                    sim = cosine_similarity(gen_emb, exp_emb)
                    best_sim = max(best_sim, sim)
                scores["semantic"].append(best_sim)

        # Calculate term overlap scores
        if expected_insights is not None and len(expected_insights) > 0:
            # Build expected term set
            expected_terms_sets = [extract_key_terms(exp) for exp in expected_insights]
            all_expected_terms = set().union(*expected_terms_sets)

            for gen_insight in generated_insights:
                gen_terms = extract_key_terms(gen_insight)
                if all_expected_terms:
                    # Calculate Jaccard similarity with union of expected terms
                    overlap = jaccard_similarity(gen_terms, all_expected_terms)
                    scores["term"].append(overlap)

        # Use manual scores if provided
        if manual_scores is not None and len(manual_scores) > 0:
            # Ensure scores are in valid range
            for score in manual_scores:
                clamped = max(0.0, min(1.0, score))
                scores["manual"].append(clamped)

        # Calculate weighted average
        total_weight = 0.0
        weighted_sum = 0.0

        if scores["semantic"]:
            semantic_avg = float(np.mean(scores["semantic"]))
            weighted_sum += semantic_weight * semantic_avg
            total_weight += semantic_weight
        else:
            semantic_avg = None

        if scores["term"]:
            term_avg = float(np.mean(scores["term"]))
            weighted_sum += term_weight * term_avg
            total_weight += term_weight
        else:
            term_avg = None

        if scores["manual"]:
            manual_avg = float(np.mean(scores["manual"]))
            weighted_sum += manual_weight * manual_avg
            total_weight += manual_weight
        else:
            manual_avg = None

        # Calculate final precision
        if total_weight > 0:
            precision = weighted_sum / total_weight
        else:
            # No signals available, return 0
            precision = 0.0

        self._last_value = precision
        self._last_metadata = {
            "num_insights": num_insights,
            "semantic_score": semantic_avg,
            "term_score": term_avg,
            "manual_score": manual_avg,
            "semantic_weight": semantic_weight,
            "term_weight": term_weight,
            "manual_weight": manual_weight,
            "components_used": sum(
                [
                    1 if scores["semantic"] else 0,
                    1 if scores["term"] else 0,
                    1 if scores["manual"] else 0,
                ]
            ),
        }

        return precision


class InsightStability(MathMetricBase):
    """
    Insight Stability (IS)

    Measures how consistent insights remain when generated from
    similar inputs over time.

    A stable reflection system should produce similar insights when
    given similar memory content. High stability indicates:
    - Deterministic insight generation
    - Consistent pattern recognition
    - Reliable knowledge extraction

    Low stability may indicate:
    - Overly sensitive to minor input variations
    - Non-deterministic LLM outputs
    - Insufficient memory clustering

    Formula (embedding-based):
        IS = mean(cosine_similarity(insight_t0, insight_t1))
             for all consecutive time pairs

    Formula (term-based):
        IS = mean(jaccard_similarity(terms_t0, terms_t1))
             for all consecutive time pairs

    Range: 0.0 (completely unstable) to 1.0 (perfectly stable)
    Typical good value: > 0.6

    Example:
        >>> stability = InsightStability()
        >>> result = stability.calculate(
        ...     insight_snapshots=[
        ...         {"timestamp": t0, "insights": [...], "embeddings": [...]},
        ...         {"timestamp": t1, "insights": [...], "embeddings": [...]},
        ...     ]
        ... )
        >>> print(f"Insight stability: {result:.2f}")
        Insight stability: 0.78
    """

    def __init__(self):
        super().__init__(
            name="insight_stability",
            description="Consistency of insights over time with similar inputs",
        )

    def calculate(
        self,
        insight_snapshots: List[Dict[str, Any]],
        use_embeddings: bool = True,
        use_terms: bool = True,
        embedding_weight: float = 0.6,
        term_weight: float = 0.4,
    ) -> float:
        """
        Calculate insight stability from multiple snapshots over time.

        Args:
            insight_snapshots: List of snapshot dictionaries, each containing:
                - "timestamp": datetime or comparable timestamp
                - "insights": List[str] of insight texts
                - "embeddings": Optional List[NDArray] of insight embeddings
            use_embeddings: Whether to use embedding similarity
            use_terms: Whether to use term-based similarity
            embedding_weight: Weight for embedding similarity
            term_weight: Weight for term similarity

        Returns:
            Stability score (0.0 to 1.0)
        """
        if len(insight_snapshots) < 2:
            self._last_value = 1.0  # Single snapshot = perfectly stable (by definition)
            self._last_metadata = {
                "num_snapshots": len(insight_snapshots),
                "reason": "Need at least 2 snapshots for stability measurement",
            }
            return 1.0

        # Sort snapshots by timestamp
        sorted_snapshots = sorted(
            insight_snapshots,
            key=lambda x: x.get("timestamp", 0),
        )

        embedding_similarities = []
        term_similarities = []

        # Compare consecutive snapshots
        for i in range(len(sorted_snapshots) - 1):
            snap_t0 = sorted_snapshots[i]
            snap_t1 = sorted_snapshots[i + 1]

            # Embedding-based similarity
            if use_embeddings:
                emb_t0 = snap_t0.get("embeddings", [])
                emb_t1 = snap_t1.get("embeddings", [])

                if emb_t0 and emb_t1:
                    # Calculate pairwise similarities and take mean
                    pair_sims = []
                    for e0 in emb_t0:
                        for e1 in emb_t1:
                            pair_sims.append(cosine_similarity(e0, e1))
                    if pair_sims:
                        embedding_similarities.append(float(np.mean(pair_sims)))

            # Term-based similarity
            if use_terms:
                insights_t0 = snap_t0.get("insights", [])
                insights_t1 = snap_t1.get("insights", [])

                if insights_t0 and insights_t1:
                    # Extract all terms from each snapshot
                    terms_t0 = set()
                    for insight in insights_t0:
                        terms_t0.update(extract_key_terms(insight))

                    terms_t1 = set()
                    for insight in insights_t1:
                        terms_t1.update(extract_key_terms(insight))

                    if terms_t0 or terms_t1:
                        term_sim = jaccard_similarity(terms_t0, terms_t1)
                        term_similarities.append(term_sim)

        # Calculate weighted stability score
        total_weight = 0.0
        weighted_sum = 0.0

        if embedding_similarities:
            emb_stability = float(np.mean(embedding_similarities))
            weighted_sum += embedding_weight * emb_stability
            total_weight += embedding_weight
        else:
            emb_stability = None

        if term_similarities:
            term_stability = float(np.mean(term_similarities))
            weighted_sum += term_weight * term_stability
            total_weight += term_weight
        else:
            term_stability = None

        if total_weight > 0:
            stability = weighted_sum / total_weight
        else:
            stability = 0.0

        self._last_value = stability
        self._last_metadata = {
            "num_snapshots": len(insight_snapshots),
            "num_comparisons": len(sorted_snapshots) - 1,
            "embedding_stability": emb_stability,
            "term_stability": term_stability,
            "embedding_weight": embedding_weight if use_embeddings else 0.0,
            "term_weight": term_weight if use_terms else 0.0,
            "embedding_comparisons": len(embedding_similarities),
            "term_comparisons": len(term_similarities),
        }

        return stability


class CriticalEventDetectionScore(MathMetricBase):
    """
    Critical Event Detection Score (CEDS)

    Measures the reflection system's ability to detect and highlight
    important events that warrant reflection.

    Critical events in RAE include:
    - Failures and errors (high importance for learning)
    - Significant successes (patterns worth remembering)
    - Anomalies in memory patterns
    - Cluster formations indicating new topics

    Formula: CEDS = F1(precision, recall)
        where:
        - precision = true_positives / (true_positives + false_positives)
        - recall = true_positives / (true_positives + false_negatives)

    Alternative: Weighted F-beta score for emphasizing precision or recall:
        F_beta = (1 + beta^2) * (precision * recall) / (beta^2 * precision + recall)

    Range: 0.0 (never detects critical events) to 1.0 (perfect detection)
    Typical good value: > 0.7

    Example:
        >>> detection = CriticalEventDetectionScore()
        >>> result = detection.calculate(
        ...     detected_events=["error_001", "anomaly_005", "success_012"],
        ...     ground_truth_events=["error_001", "anomaly_005", "error_003"],
        ... )
        >>> print(f"Detection score: {result:.2f}")
        Detection score: 0.67
    """

    def __init__(self):
        super().__init__(
            name="critical_event_detection_score",
            description="Ability to detect important events requiring reflection",
        )

    def calculate(
        self,
        detected_events: List[str],
        ground_truth_events: List[str],
        beta: float = 1.0,
        event_weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Calculate critical event detection score.

        Args:
            detected_events: List of event IDs detected by the system
            ground_truth_events: List of event IDs that should have been detected
            beta: F-beta parameter. beta=1 gives F1 (balanced).
                  beta>1 emphasizes recall, beta<1 emphasizes precision.
            event_weights: Optional dict mapping event_id to importance weight.
                          Used for weighted precision/recall calculation.

        Returns:
            F-beta score (0.0 to 1.0)
        """
        detected_set = set(detected_events)
        ground_truth_set = set(ground_truth_events)

        if not ground_truth_set:
            # No critical events to detect
            if not detected_set:
                # Perfect score if nothing to detect and nothing detected
                self._last_value = 1.0
                self._last_metadata = {
                    "num_detected": 0,
                    "num_ground_truth": 0,
                    "reason": "No critical events in ground truth",
                }
                return 1.0
            else:
                # False positives only
                self._last_value = 0.0
                self._last_metadata = {
                    "num_detected": len(detected_set),
                    "num_ground_truth": 0,
                    "false_positives": len(detected_set),
                    "reason": "Detected events when none expected",
                }
                return 0.0

        # Calculate true positives, false positives, false negatives
        true_positives = detected_set & ground_truth_set
        false_positives = detected_set - ground_truth_set
        false_negatives = ground_truth_set - detected_set

        # Calculate weighted or unweighted metrics
        if event_weights:
            # Weighted calculation
            tp_weight = sum(event_weights.get(e, 1.0) for e in true_positives)
            fp_weight = sum(event_weights.get(e, 1.0) for e in false_positives)
            fn_weight = sum(event_weights.get(e, 1.0) for e in false_negatives)

            if tp_weight + fp_weight > 0:
                precision = tp_weight / (tp_weight + fp_weight)
            else:
                precision = 0.0

            if tp_weight + fn_weight > 0:
                recall = tp_weight / (tp_weight + fn_weight)
            else:
                recall = 0.0
        else:
            # Unweighted calculation
            if len(true_positives) + len(false_positives) > 0:
                precision = len(true_positives) / (
                    len(true_positives) + len(false_positives)
                )
            else:
                precision = 0.0

            if len(true_positives) + len(false_negatives) > 0:
                recall = len(true_positives) / (
                    len(true_positives) + len(false_negatives)
                )
            else:
                recall = 0.0

        # Calculate F-beta score
        if precision + recall > 0:
            beta_squared = beta * beta
            f_beta = (
                (1 + beta_squared)
                * (precision * recall)
                / (beta_squared * precision + recall)
            )
        else:
            f_beta = 0.0

        self._last_value = f_beta
        self._last_metadata = {
            "num_detected": len(detected_set),
            "num_ground_truth": len(ground_truth_set),
            "true_positives": len(true_positives),
            "false_positives": len(false_positives),
            "false_negatives": len(false_negatives),
            "precision": precision,
            "recall": recall,
            "f1_score": calculate_f1_score(precision, recall),
            "beta": beta,
            "weighted": event_weights is not None,
        }

        return f_beta


class ContradictionAvoidanceScore(MathMetricBase):
    """
    Contradiction Avoidance Score (CAS)

    Measures the logical consistency of generated insights by detecting
    contradictions within the insight set.

    A high-quality reflection system should avoid generating contradictory
    insights. Contradictions indicate:
    - Inconsistent pattern recognition
    - Conflicting lessons learned
    - Potential for confusing downstream consumers

    Formula: CAS = 1.0 - (contradiction_count / total_insight_pairs)

    Where contradiction_count is the number of insight pairs that
    contradict each other, detected via:
    1. Semantic analysis (embedding similarity + negation)
    2. Term-based negation patterns
    3. Optional NLI model scores

    Range: 0.0 (many contradictions) to 1.0 (no contradictions)
    Typical good value: > 0.9

    Example:
        >>> consistency = ContradictionAvoidanceScore()
        >>> result = consistency.calculate(
        ...     insights=[
        ...         "Caching improves performance significantly",
        ...         "Database indexes are essential for queries",
        ...         "Caching has no effect on performance",  # Contradiction!
        ...     ],
        ...     insight_embeddings=[emb1, emb2, emb3],
        ... )
        >>> print(f"Consistency score: {result:.2f}")
        Consistency score: 0.67
    """

    def __init__(self):
        super().__init__(
            name="contradiction_avoidance_score",
            description="Logical consistency and absence of contradictions in insights",
        )

    def calculate(
        self,
        insights: List[str],
        insight_embeddings: Optional[List[NDArray[np.float32]]] = None,
        contradiction_threshold: float = 0.5,
        pairwise_scores: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        """
        Calculate contradiction avoidance score for a set of insights.

        Args:
            insights: List of insight texts to analyze
            insight_embeddings: Optional embeddings for semantic analysis
            contradiction_threshold: Score threshold above which a pair
                                    is considered contradictory (0.0-1.0)
            pairwise_scores: Optional pre-computed contradiction scores
                            for each pair, as list of dicts with:
                            - "pair": (index_i, index_j)
                            - "score": float (contradiction score 0-1)

        Returns:
            Contradiction avoidance score (0.0 to 1.0)
        """
        if len(insights) < 2:
            self._last_value = 1.0  # Single insight cannot contradict itself
            self._last_metadata = {
                "num_insights": len(insights),
                "num_pairs": 0,
                "reason": "Need at least 2 insights for contradiction detection",
            }
            return 1.0

        num_insights = len(insights)
        total_pairs = (num_insights * (num_insights - 1)) // 2
        contradiction_count = 0
        contradiction_pairs = []

        # Use pre-computed scores if available
        if pairwise_scores is not None:
            for score_entry in pairwise_scores:
                score = score_entry.get("score", 0.0)
                if score >= contradiction_threshold:
                    contradiction_count += 1
                    contradiction_pairs.append(score_entry.get("pair"))
        else:
            # Compute contradiction scores for all pairs
            for i in range(num_insights):
                for j in range(i + 1, num_insights):
                    # Get embeddings if available
                    emb_i = None
                    emb_j = None
                    if insight_embeddings is not None:
                        if i < len(insight_embeddings):
                            emb_i = insight_embeddings[i]
                        if j < len(insight_embeddings):
                            emb_j = insight_embeddings[j]

                    # Detect contradiction
                    is_contradiction, score = detect_contradiction(
                        insights[i],
                        insights[j],
                        emb_i,
                        emb_j,
                        contradiction_threshold=contradiction_threshold,
                    )

                    if is_contradiction:
                        contradiction_count += 1
                        contradiction_pairs.append((i, j))

        # Calculate avoidance score
        if total_pairs > 0:
            contradiction_ratio = contradiction_count / total_pairs
            avoidance_score = 1.0 - contradiction_ratio
        else:
            avoidance_score = 1.0

        self._last_value = avoidance_score
        self._last_metadata = {
            "num_insights": num_insights,
            "total_pairs": total_pairs,
            "contradiction_count": contradiction_count,
            "contradiction_ratio": (
                contradiction_count / total_pairs if total_pairs > 0 else 0.0
            ),
            "contradiction_threshold": contradiction_threshold,
            "contradicting_pairs": contradiction_pairs[:10],  # Limit to first 10
            "embeddings_used": insight_embeddings is not None,
        }

        return avoidance_score
