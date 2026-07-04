"""
Query Inspector Page - Test and Analyze Queries

Test search queries and inspect results with scoring analysis.
"""

import os
import sys

import pandas as pd
import streamlit as st

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.visualizations import (
    apply_custom_css,
    create_score_distribution,
    format_memory_preview,
    format_timestamp,
)

# Apply styling
apply_custom_css()

# Page title
st.title("🔍 Query Inspector")
st.markdown("Test search queries and analyze results with detailed scoring")

# Check connection
if "client" not in st.session_state or not st.session_state.get("connected", False):
    st.error("❌ Not connected to RAE API")
    st.info("👈 Please configure connection in the main page")
    st.stop()

client = st.session_state.client

st.divider()

# Initialize session state
if "query_results" not in st.session_state:
    st.session_state.query_results = None
if "query_history" not in st.session_state:
    st.session_state.query_history = []
if "comparison_mode" not in st.session_state:
    st.session_state.comparison_mode = False

# Mode selector
col1, col2 = st.columns(2)

with col1:
    if st.button(
        "🔍 Single Query Mode",
        type="primary" if not st.session_state.comparison_mode else "secondary",
        use_container_width=True,
    ):
        st.session_state.comparison_mode = False
        st.rerun()

with col2:
    if st.button(
        "⚖️ Comparison Mode",
        type="primary" if st.session_state.comparison_mode else "secondary",
        use_container_width=True,
    ):
        st.session_state.comparison_mode = True
        st.rerun()

st.divider()

# =============================================================================
# SINGLE QUERY MODE
# =============================================================================
if not st.session_state.comparison_mode:
    st.header("🔍 Single Query Inspector")

    # Query input
    query_text = st.text_area(
        "Query Text",
        placeholder="Enter your search query...",
        height=100,
        help="The query to search for in memory",
    )

    # Query parameters
    col1, col2, col3 = st.columns(3)

    with col1:
        top_k = st.slider(
            "Top K Results",
            min_value=1,
            max_value=50,
            value=10,
            help="Number of top results to return",
        )

    with col2:
        use_rerank = st.checkbox(
            "Use Reranking", value=True, help="Apply reranking to results"
        )

    with col3:
        show_scores = st.checkbox(
            "Show Detailed Scores", value=True, help="Display score breakdown"
        )

    # Advanced filters
    with st.expander("🔧 Advanced Filters"):
        col1, col2, col3 = st.columns(3)

        with col1:
            filter_layers = st.multiselect(
                "Memory Layers",
                options=["em", "wm", "sm", "ltm"],
                default=[],
                help="Filter by memory layer",
            )

        with col2:
            filter_tags = st.text_input(
                "Tags (comma-separated)",
                placeholder="tag1, tag2, tag3",
                help="Filter by tags",
            )

        with col3:
            filter_source = st.text_input(
                "Source", placeholder="Filter by source", help="Filter by memory source"
            )

    # Execute query
    if st.button("🚀 Execute Query", type="primary", use_container_width=True):
        if not query_text.strip():
            st.warning("Please enter a query")
        else:
            try:
                with st.spinner("Executing query..."):
                    # Build filters
                    filters = {}
                    if filter_layers:
                        filters["layer"] = (
                            filter_layers[0]
                            if len(filter_layers) == 1
                            else filter_layers
                        )
                    if filter_source:
                        filters["source"] = filter_source

                    # Execute query
                    results = client.query_memory(
                        query=query_text, top_k=top_k, use_rerank=use_rerank
                    )

                    # Filter by tags if specified
                    if filter_tags:
                        tag_list = [tag.strip() for tag in filter_tags.split(",")]
                        results = [
                            r
                            for r in results
                            if any(tag in r.get("tags", []) for tag in tag_list)
                        ]

                    # Store results
                    st.session_state.query_results = {
                        "query": query_text,
                        "results": results,
                        "top_k": top_k,
                        "use_rerank": use_rerank,
                        "filters": filters,
                    }

                    # Add to history
                    st.session_state.query_history.insert(
                        0,
                        {
                            "query": query_text,
                            "count": len(results),
                            "timestamp": pd.Timestamp.now(),
                        },
                    )
                    st.session_state.query_history = st.session_state.query_history[
                        :10
                    ]  # Keep last 10

                    st.success(f"✓ Query executed - Found {len(results)} results")

            except Exception as e:
                st.error(f"Error executing query: {e}")
                st.exception(e)

    # Display results
    if st.session_state.query_results:
        results_data = st.session_state.query_results
        results = results_data["results"]

        if results:
            st.divider()
            st.header("📊 Query Results")

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Results", len(results))

            with col2:
                avg_score = sum(r.get("score", 0) for r in results) / len(results)
                st.metric("Average Score", f"{avg_score:.4f}")

            with col3:
                max_score = max((r.get("score", 0) for r in results), default=0)
                st.metric("Max Score", f"{max_score:.4f}")

            with col4:
                min_score = min((r.get("score", 0) for r in results), default=0)
                st.metric("Min Score", f"{min_score:.4f}")

            st.divider()

            # Score distribution
            st.subheader("📈 Score Distribution")

            try:
                fig = create_score_distribution(results)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating chart: {e}")

            st.divider()

            # Results tabs
            tab1, tab2, tab3 = st.tabs(
                ["🎯 Ranked Results", "📋 Table View", "📊 Analysis"]
            )

            with tab1:
                st.subheader("Ranked Results")

                for i, result in enumerate(results, 1):
                    with st.expander(
                        f"#{i} - Score: {result.get('score', 0):.4f} - {format_memory_preview(result.get('content', ''), 80)}"
                    ):
                        # Result header
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.markdown(f"**ID:** `{result.get('id', 'N/A')}`")
                            st.markdown(f"**Layer:** {result.get('layer', 'N/A')}")

                        with col2:
                            if show_scores:
                                st.metric("Score", f"{result.get('score', 0):.4f}")

                        st.divider()

                        # Content
                        st.markdown("**Content:**")
                        st.text(result.get("content", "No content"))

                        # Metadata
                        col1, col2 = st.columns(2)

                        with col1:
                            st.caption(f"**Source:** {result.get('source', 'N/A')}")
                            if "timestamp" in result:
                                st.caption(
                                    f"**Timestamp:** {format_timestamp(result['timestamp'])}"
                                )

                        with col2:
                            if "tags" in result and result["tags"]:
                                st.caption(f"**Tags:** {', '.join(result['tags'])}")

                        # Score breakdown (if available)
                        if show_scores and "score" in result:
                            st.markdown("**Score Details:**")
                            st.caption(f"Relevance Score: {result['score']:.4f}")

            with tab2:
                st.subheader("Table View")

                # Convert to dataframe
                df = pd.DataFrame(results)

                # Select columns to display
                available_columns = df.columns.tolist()
                default_columns = [
                    "id",
                    "content",
                    "layer",
                    "score",
                    "source",
                    "timestamp",
                ]
                default_columns = [
                    col for col in default_columns if col in available_columns
                ]

                display_columns = st.multiselect(
                    "Select Columns", options=available_columns, default=default_columns
                )

                if display_columns:
                    st.dataframe(
                        df[display_columns], use_container_width=True, height=400
                    )
                else:
                    st.dataframe(df, use_container_width=True, height=400)

                # Export results
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv,
                    file_name=f"query_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )

            with tab3:
                st.subheader("Query Analysis")

                # Layer distribution
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Layer Distribution:**")
                    layer_counts = {}
                    for result in results:
                        layer = result.get("layer", "unknown")
                        layer_counts[layer] = layer_counts.get(layer, 0) + 1

                    for layer, count in sorted(
                        layer_counts.items(), key=lambda x: x[1], reverse=True
                    ):
                        st.write(
                            f"**{layer}:** {count} ({count / len(results) * 100:.1f}%)"
                        )

                with col2:
                    st.markdown("**Score Statistics:**")
                    scores = [r.get("score", 0) for r in results]
                    st.write(f"**Mean:** {pd.Series(scores).mean():.4f}")
                    st.write(f"**Median:** {pd.Series(scores).median():.4f}")
                    st.write(f"**Std Dev:** {pd.Series(scores).std():.4f}")
                    st.write(f"**Range:** {min(scores):.4f} - {max(scores):.4f}")

                st.divider()

                # Source distribution
                st.markdown("**Source Distribution:**")
                source_counts = {}
                for result in results:
                    source = result.get("source", "unknown")
                    source_counts[source] = source_counts.get(source, 0) + 1

                for source, count in sorted(
                    source_counts.items(), key=lambda x: x[1], reverse=True
                )[:10]:
                    st.write(f"**{source}:** {count}")

        else:
            st.info("No results found for this query")

# =============================================================================
# COMPARISON MODE
# =============================================================================
else:
    st.header("⚖️ Query Comparison Mode")

    st.info("Compare results from multiple queries side by side")

    # Query A
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Query A")
        query_a = st.text_area(
            "Query A", placeholder="Enter first query...", height=80, key="query_a"
        )
        top_k_a = st.slider("Top K", 1, 20, 5, key="top_k_a")

    with col2:
        st.subheader("Query B")
        query_b = st.text_area(
            "Query B", placeholder="Enter second query...", height=80, key="query_b"
        )
        top_k_b = st.slider("Top K", 1, 20, 5, key="top_k_b")

    # Execute comparison
    if st.button("⚖️ Compare Queries", type="primary", use_container_width=True):
        if not query_a.strip() or not query_b.strip():
            st.warning("Please enter both queries")
        else:
            try:
                with st.spinner("Executing queries..."):
                    # Execute both queries
                    results_a = client.query_memory(query=query_a, top_k=top_k_a)
                    results_b = client.query_memory(query=query_b, top_k=top_k_b)

                    st.session_state.comparison_results = {
                        "query_a": query_a,
                        "results_a": results_a,
                        "query_b": query_b,
                        "results_b": results_b,
                    }

                    st.success("✓ Both queries executed")

            except Exception as e:
                st.error(f"Error executing queries: {e}")

    # Display comparison
    if "comparison_results" in st.session_state:
        comp = st.session_state.comparison_results

        st.divider()
        st.header("📊 Comparison Results")

        # Summary comparison
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            st.metric("Query A Results", len(comp["results_a"]))
            if comp["results_a"]:
                avg_score_a = sum(r.get("score", 0) for r in comp["results_a"]) / len(
                    comp["results_a"]
                )
                st.metric("Avg Score A", f"{avg_score_a:.4f}")

        with col2:
            st.metric("Query B Results", len(comp["results_b"]))
            if comp["results_b"]:
                avg_score_b = sum(r.get("score", 0) for r in comp["results_b"]) / len(
                    comp["results_b"]
                )
                st.metric("Avg Score B", f"{avg_score_b:.4f}")

        with col3:
            # Find overlap
            ids_a = {r.get("id") for r in comp["results_a"]}
            ids_b = {r.get("id") for r in comp["results_b"]}
            overlap = ids_a & ids_b
            st.metric("Overlapping Results", len(overlap))

        st.divider()

        # Side-by-side results
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Query A Results")
            st.caption(f"Query: {comp['query_a']}")

            for i, result in enumerate(comp["results_a"], 1):
                overlap_marker = "⭐" if result.get("id") in overlap else ""
                with st.container():
                    st.markdown(
                        f"**#{i} {overlap_marker}** - Score: {result.get('score', 0):.4f}"
                    )
                    st.caption(format_memory_preview(result.get("content", ""), 100))
                    st.divider()

        with col2:
            st.subheader("Query B Results")
            st.caption(f"Query: {comp['query_b']}")

            for i, result in enumerate(comp["results_b"], 1):
                overlap_marker = "⭐" if result.get("id") in overlap else ""
                with st.container():
                    st.markdown(
                        f"**#{i} {overlap_marker}** - Score: {result.get('score', 0):.4f}"
                    )
                    st.caption(format_memory_preview(result.get("content", ""), 100))
                    st.divider()

        # Overlap details
        if overlap:
            st.divider()
            st.subheader("⭐ Overlapping Results")
            st.caption(f"These {len(overlap)} results appeared in both queries")

            for mem_id in overlap:
                # Find in both results
                mem_a = next(
                    (r for r in comp["results_a"] if r.get("id") == mem_id), None
                )
                mem_b = next(
                    (r for r in comp["results_b"] if r.get("id") == mem_id), None
                )

                if mem_a and mem_b:
                    with st.expander(f"ID: {mem_id}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**Query A:**")
                            st.metric("Score", f"{mem_a.get('score', 0):.4f}")

                        with col2:
                            st.markdown("**Query B:**")
                            st.metric("Score", f"{mem_b.get('score', 0):.4f}")

                        st.markdown("**Content:**")
                        st.text(mem_a.get("content", ""))

st.divider()

# Query history
if st.session_state.query_history:
    with st.expander("📜 Query History (Last 10)"):
        for i, hist in enumerate(st.session_state.query_history, 1):
            st.caption(
                f"{i}. **{hist['query'][:50]}...** ({hist['count']} results) - {hist['timestamp'].strftime('%H:%M:%S')}"
            )

# Help section
with st.expander("ℹ️ Help - Query Inspector"):
    st.markdown(
        """
    **Single Query Mode:**
    - Enter a query and adjust parameters
    - Execute query to see ranked results
    - View score distribution and analysis
    - Export results to CSV

    **Comparison Mode:**
    - Test two queries side by side
    - Compare result sets and scores
    - Identify overlapping results (marked with ⭐)
    - Useful for query optimization

    **Tips:**
    - Higher scores indicate better relevance
    - Use filters to narrow results
    - Reranking can improve result quality
    - Top K controls number of results
    - Compare different phrasings to optimize queries
    """
    )

st.caption("RAE Memory Dashboard - Query Inspector")
