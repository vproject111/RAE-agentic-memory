"""
Visualization Utilities for RAE Dashboard

Helper functions for creating charts and graphs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def create_timeline_chart(memories: List[Dict[str, Any]]) -> go.Figure:
    """
    Create interactive timeline scatter plot.

    Args:
        memories: List of memory dictionaries

    Returns:
        Plotly figure
    """
    if not memories:
        return go.Figure()

    df = pd.DataFrame(memories)

    # Ensure timestamp is datetime
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    else:
        df["timestamp"] = datetime.now()

    # Create scatter plot
    fig = px.scatter(
        df,
        x="timestamp",
        y="layer",
        color="layer",
        hover_data={
            "content": True,
            "source": True,
            "timestamp": "|%Y-%m-%d %H:%M",
            "layer": False,
        },
        title="Memory Timeline",
        labels={"timestamp": "Time", "layer": "Memory Layer"},
        color_discrete_map={
            "em": "#FF6B6B",
            "episodic": "#FF6B6B",
            "wm": "#4ECDC4",
            "working": "#4ECDC4",
            "sm": "#45B7D1",
            "semantic": "#45B7D1",
            "ltm": "#96CEB4",
            "long-term": "#96CEB4",
        },
    )

    fig.update_layout(
        height=500,
        hovermode="closest",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    fig.update_traces(
        marker=dict(size=12, line=dict(width=2, color="white")),
        selector=dict(mode="markers"),
    )

    return fig


def create_layer_distribution_chart(memories: List[Dict[str, Any]]) -> go.Figure:
    """
    Create pie chart of memory layer distribution.

    Args:
        memories: List of memory dictionaries

    Returns:
        Plotly figure
    """
    if not memories:
        return go.Figure()

    df = pd.DataFrame(memories)

    layer_counts = df["layer"].value_counts()

    fig = px.pie(
        values=layer_counts.values,
        names=layer_counts.index,
        title="Memory Distribution by Layer",
        color_discrete_map={
            "em": "#FF6B6B",
            "episodic": "#FF6B6B",
            "wm": "#4ECDC4",
            "working": "#4ECDC4",
            "sm": "#45B7D1",
            "semantic": "#45B7D1",
            "ltm": "#96CEB4",
            "long-term": "#96CEB4",
        },
    )

    fig.update_layout(
        height=400,
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def create_tags_wordcloud_chart(memories: List[Dict[str, Any]]) -> go.Figure:
    """
    Create tag frequency bar chart.

    Args:
        memories: List of memory dictionaries

    Returns:
        Plotly figure
    """
    if not memories:
        return go.Figure()

    # Extract all tags
    tags = []
    for memory in memories:
        if "tags" in memory and memory["tags"]:
            tags.extend(memory["tags"])

    if not tags:
        return go.Figure()

    # Count tag frequencies
    tag_counts = pd.Series(tags).value_counts().head(20)

    fig = px.bar(
        x=tag_counts.values,
        y=tag_counts.index,
        orientation="h",
        title="Top 20 Tags",
        labels={"x": "Count", "y": "Tag"},
        color=tag_counts.values,
        color_continuous_scale="Viridis",
    )

    fig.update_layout(
        height=600,
        showlegend=False,
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def create_temporal_heatmap(memories: List[Dict[str, Any]]) -> go.Figure:
    """
    Create heatmap of memory activity over time.

    Args:
        memories: List of memory dictionaries

    Returns:
        Plotly figure
    """
    if not memories:
        return go.Figure()

    df = pd.DataFrame(memories)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Extract hour and day of week
    df["hour"] = df["timestamp"].dt.hour
    df["day"] = df["timestamp"].dt.day_name()

    # Create pivot table
    heatmap_data = df.groupby(["day", "hour"]).size().unstack(fill_value=0)

    # Reorder days
    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    heatmap_data = heatmap_data.reindex(
        [d for d in day_order if d in heatmap_data.index]
    )

    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Hour of Day", y="Day of Week", color="Activity"),
        title="Memory Activity Heatmap",
        color_continuous_scale="YlOrRd",
    )

    fig.update_layout(
        height=400,
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def create_score_distribution(results: List[Dict[str, Any]]) -> go.Figure:
    """
    Create distribution plot of search scores.

    Args:
        results: List of search result dictionaries

    Returns:
        Plotly figure
    """
    if not results:
        return go.Figure()

    scores = [r.get("score", 0) for r in results]

    fig = go.Figure(data=[go.Histogram(x=scores, nbinsx=20, marker_color="#4ECDC4")])

    fig.update_layout(
        title="Search Score Distribution",
        xaxis_title="Score",
        yaxis_title="Count",
        height=300,
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def format_memory_preview(content: str, max_length: int = 100) -> str:
    """
    Format memory content for preview.

    Args:
        content: Memory content text
        max_length: Maximum preview length

    Returns:
        Formatted preview string
    """
    if len(content) <= max_length:
        return content

    return content[:max_length] + "..."


def format_timestamp(timestamp: Any) -> str:
    """
    Format timestamp for display.

    Args:
        timestamp: Timestamp (string or datetime)

    Returns:
        Formatted timestamp string
    """
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp)
        except Exception:
            return timestamp
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        return str(timestamp)

    return dt.strftime("%Y-%m-%d %H:%M:%S")


def create_metric_card(label: str, value: Any, delta: Optional[str] = None):
    """
    Create styled metric card.

    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta value
    """
    if delta:
        st.metric(label, value, delta)
    else:
        st.metric(label, value)


def display_memory_card(memory: Dict[str, Any], show_actions: bool = True):
    """
    Display a memory as a styled card.

    Args:
        memory: Memory dictionary
        show_actions: Whether to show action buttons
    """
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"**ID:** `{memory.get('id', 'N/A')}`")
            st.markdown(f"**Content:** {memory.get('content', 'N/A')}")

        with col2:
            st.markdown(f"**Layer:** {memory.get('layer', 'N/A')}")
            if "score" in memory:
                st.markdown(f"**Score:** {memory['score']:.3f}")

        # Metadata
        col3, col4 = st.columns(2)

        with col3:
            if "source" in memory:
                st.caption(f"Source: {memory['source']}")
            if "timestamp" in memory:
                st.caption(f"Time: {format_timestamp(memory['timestamp'])}")

        with col4:
            if "tags" in memory and memory["tags"]:
                tags_str = ", ".join(memory["tags"])
                st.caption(f"Tags: {tags_str}")

        if show_actions:
            st.divider()


def apply_custom_css():
    """Apply custom CSS styling to the dashboard."""
    st.markdown(
        """
        <style>
        .main {
            padding: 2rem;
        }

        .stMetric {
            background-color: rgba(28, 131, 225, 0.1);
            border: 1px solid rgba(28, 131, 225, 0.2);
            padding: 1rem;
            border-radius: 0.5rem;
        }

        .stButton>button {
            width: 100%;
        }

        .memory-card {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
        }

        h1 {
            color: #4ECDC4;
        }

        h2, h3 {
            color: #45B7D1;
        }

        .stExpander {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 0.5rem;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
