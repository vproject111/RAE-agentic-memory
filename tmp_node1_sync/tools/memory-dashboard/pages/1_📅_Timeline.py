"""
Timeline Page - Memory Timeline Visualization

View and analyze memory timeline with interactive charts.
"""

import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import get_cached_memories
from utils.visualizations import (
    apply_custom_css,
    create_temporal_heatmap,
    create_timeline_chart,
    format_timestamp,
)

# Apply styling
apply_custom_css()

# Page title
st.title("📅 Memory Timeline")
st.markdown("Visualize and explore memory history over time")

# Check connection
if "client" not in st.session_state or not st.session_state.get("connected", False):
    st.error("❌ Not connected to RAE API")
    st.info("👈 Please configure connection in the main page")
    st.stop()

client = st.session_state.client

st.divider()

# Filters section
st.header("🔍 Filters")

col1, col2, col3 = st.columns(3)

with col1:
    layer_filter = st.multiselect(
        "Memory Layers",
        options=["em", "wm", "sm", "ltm"],
        default=["em", "wm"],
        help="Select which memory layers to display",
    )

with col2:
    days_back = st.slider(
        "Days Back",
        min_value=1,
        max_value=90,
        value=7,
        help="Number of days to look back",
    )

with col3:
    sort_by = st.selectbox(
        "Sort By",
        options=["timestamp", "layer", "source"],
        help="Sort memories by field",
    )

st.divider()

# Fetch memories
try:
    with st.spinner("Loading memories..."):
        memories = get_cached_memories(client, tuple(layer_filter), days_back)

    if not memories:
        st.warning("No memories found with current filters")
        st.info("Try adjusting the filters or increasing the time range")
        st.stop()

    st.success(f"✓ Loaded {len(memories)} memories")

except Exception as e:
    st.error(f"Error loading memories: {e}")
    st.stop()

# Timeline visualization
st.header("📊 Timeline Visualization")

tab1, tab2, tab3 = st.tabs(["Scatter Plot", "Heatmap", "Table View"])

with tab1:
    try:
        fig = create_timeline_chart(memories)
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            """
        **Interactive Chart:** Hover over points to see details.
        Click and drag to zoom, double-click to reset.
        """
        )

    except Exception as e:
        st.error(f"Error creating timeline chart: {e}")

with tab2:
    try:
        fig = create_temporal_heatmap(memories)
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            """
        **Activity Heatmap:** Shows when memories are most frequently created.
        Darker colors indicate higher activity.
        """
        )

    except Exception as e:
        st.error(f"Error creating heatmap: {e}")

with tab3:
    try:
        df = pd.DataFrame(memories)

        # Ensure timestamp column exists
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Sort dataframe
        if sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=False)

        # Display configuration
        display_columns = st.multiselect(
            "Display Columns",
            options=df.columns.tolist(),
            default=["id", "content", "layer", "timestamp", "tags"][: len(df.columns)],
        )

        if display_columns:
            st.dataframe(df[display_columns], use_container_width=True, height=400)
        else:
            st.dataframe(df, use_container_width=True, height=400)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"rae_memories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Error displaying table: {e}")

st.divider()

# Statistics
st.header("📈 Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Memories", len(memories))

with col2:
    if memories:
        layers = [m.get("layer", "unknown") for m in memories]
        most_common = max(set(layers), key=layers.count)
        st.metric("Most Common Layer", most_common)

with col3:
    if memories:
        all_tags = []
        for m in memories:
            if "tags" in m and m["tags"]:
                all_tags.extend(m["tags"])
        st.metric("Unique Tags", len(set(all_tags)))

with col4:
    if memories:
        df = pd.DataFrame(memories)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            date_range = (df["timestamp"].max() - df["timestamp"].min()).days
            st.metric("Date Range (days)", date_range)

st.divider()

# Detailed memory list
st.header("📋 Memory Details")

# Pagination
items_per_page = st.select_slider("Items per page", options=[10, 25, 50, 100], value=25)

total_pages = (len(memories) - 1) // items_per_page + 1

if "timeline_page" not in st.session_state:
    st.session_state.timeline_page = 1

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    if st.button("⬅️ Previous", disabled=st.session_state.timeline_page <= 1):
        st.session_state.timeline_page -= 1
        st.rerun()

with col2:
    st.markdown(
        f"<center>Page {st.session_state.timeline_page} of {total_pages}</center>",
        unsafe_allow_html=True,
    )

with col3:
    if st.button("Next ➡️", disabled=st.session_state.timeline_page >= total_pages):
        st.session_state.timeline_page += 1
        st.rerun()

# Display memories for current page
start_idx = (st.session_state.timeline_page - 1) * items_per_page
end_idx = start_idx + items_per_page
page_memories = memories[start_idx:end_idx]

for i, memory in enumerate(page_memories, start=start_idx + 1):
    with st.expander(
        f"#{i} - {memory.get('layer', 'N/A')} - {format_timestamp(memory.get('timestamp', ''))}"
    ):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown("**Content:**")
            st.text(memory.get("content", "No content"))

        with col2:
            st.markdown("**Metadata:**")
            st.caption(f"ID: `{memory.get('id', 'N/A')}`")
            st.caption(f"Layer: {memory.get('layer', 'N/A')}")
            st.caption(f"Source: {memory.get('source', 'N/A')}")

        if "tags" in memory and memory["tags"]:
            st.markdown("**Tags:**")
            st.write(", ".join(memory["tags"]))

        if "score" in memory:
            st.markdown(f"**Score:** {memory['score']:.4f}")

st.divider()
st.caption("RAE Memory Dashboard - Timeline View")
