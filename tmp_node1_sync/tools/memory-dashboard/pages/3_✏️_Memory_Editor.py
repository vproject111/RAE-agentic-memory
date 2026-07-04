"""
Memory Editor Page - Edit and Manage Memories

Search, view, edit, and delete individual memories.
"""

import os
import sys

import streamlit as st

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.visualizations import (
    apply_custom_css,
    format_memory_preview,
    format_timestamp,
)

# Apply styling
apply_custom_css()

# Page title
st.title("✏️ Memory Editor")
st.markdown("Search, edit, and manage individual memories")

# Check connection
if "client" not in st.session_state or not st.session_state.get("connected", False):
    st.error("❌ Not connected to RAE API")
    st.info("👈 Please configure connection in the main page")
    st.stop()

client = st.session_state.client

st.divider()

# Initialize session state for editor
if "selected_memory" not in st.session_state:
    st.session_state.selected_memory = None
if "editor_mode" not in st.session_state:
    st.session_state.editor_mode = "search"  # "search", "edit", "create"

# Mode selector
col1, col2, col3 = st.columns(3)

with col1:
    if st.button(
        "🔍 Search Mode",
        type="primary" if st.session_state.editor_mode == "search" else "secondary",
        use_container_width=True,
    ):
        st.session_state.editor_mode = "search"
        st.session_state.selected_memory = None
        st.rerun()

with col2:
    if st.button(
        "✏️ Edit Mode",
        type="primary" if st.session_state.editor_mode == "edit" else "secondary",
        use_container_width=True,
        disabled=st.session_state.selected_memory is None,
    ):
        st.session_state.editor_mode = "edit"
        st.rerun()

with col3:
    if st.button(
        "➕ Create New",
        type="primary" if st.session_state.editor_mode == "create" else "secondary",
        use_container_width=True,
    ):
        st.session_state.editor_mode = "create"
        st.session_state.selected_memory = None
        st.rerun()

st.divider()

# =============================================================================
# SEARCH MODE
# =============================================================================
if st.session_state.editor_mode == "search":
    st.header("🔍 Search Memories")

    # Search controls
    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "Search Query",
            placeholder="Enter search terms...",
            help="Search for memories by content",
        )

    with col2:
        search_limit = st.number_input(
            "Max Results",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
            help="Maximum number of results to return",
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

    # Search button
    if st.button("🔍 Search", type="primary", use_container_width=True):
        if not search_query:
            st.warning("Please enter a search query")
        else:
            try:
                with st.spinner("Searching memories..."):
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

                    # Search memories
                    results = client.search_memories(
                        query=search_query,
                        top_k=search_limit,
                        filters=filters if filters else None,
                    )

                    # Filter by tags if specified
                    if filter_tags:
                        tag_list = [tag.strip() for tag in filter_tags.split(",")]
                        results = [
                            r
                            for r in results
                            if any(tag in r.get("tags", []) for tag in tag_list)
                        ]

                    st.session_state.search_results = results

            except Exception as e:
                st.error(f"Error searching memories: {e}")
                st.exception(e)

    # Display search results
    if "search_results" in st.session_state and st.session_state.search_results:
        results = st.session_state.search_results

        st.success(f"Found {len(results)} memories")

        st.divider()
        st.subheader("📋 Search Results")

        # Display results
        for i, memory in enumerate(results, 1):
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 1])

                with col1:
                    st.caption(f"**Rank:** {i}")
                    if "score" in memory:
                        st.caption(f"**Score:** {memory['score']:.4f}")

                with col2:
                    st.markdown(f"**ID:** `{memory.get('id', 'N/A')}`")
                    st.markdown(
                        f"**Content:** {format_memory_preview(memory.get('content', ''), 150)}"
                    )

                    # Metadata
                    metadata_parts = []
                    metadata_parts.append(f"**Layer:** {memory.get('layer', 'N/A')}")
                    if "source" in memory:
                        metadata_parts.append(f"**Source:** {memory.get('source')}")
                    if "timestamp" in memory:
                        metadata_parts.append(
                            f"**Time:** {format_timestamp(memory.get('timestamp'))}"
                        )

                    st.caption(" | ".join(metadata_parts))

                    if "tags" in memory and memory["tags"]:
                        st.caption(f"**Tags:** {', '.join(memory['tags'])}")

                with col3:
                    if st.button(
                        "✏️ Edit",
                        key=f"edit_{memory.get('id')}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_memory = memory
                        st.session_state.editor_mode = "edit"
                        st.rerun()

                st.divider()

    elif "search_results" in st.session_state and not st.session_state.search_results:
        st.info("No memories found matching your search criteria")

# =============================================================================
# EDIT MODE
# =============================================================================
elif st.session_state.editor_mode == "edit" and st.session_state.selected_memory:
    st.header("✏️ Edit Memory")

    memory = st.session_state.selected_memory

    # Display memory info
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Memory ID", memory.get("id", "N/A"))

    with col2:
        st.metric("Layer", memory.get("layer", "N/A"))

    with col3:
        if "timestamp" in memory:
            st.metric("Created", format_timestamp(memory["timestamp"])[:10])

    st.divider()

    # Edit form
    with st.form("edit_memory_form"):
        st.subheader("📝 Memory Details")

        # Content editor
        new_content = st.text_area(
            "Content",
            value=memory.get("content", ""),
            height=200,
            help="Edit the memory content",
        )

        # Tags editor
        current_tags = ", ".join(memory.get("tags", []))
        new_tags_str = st.text_input(
            "Tags (comma-separated)", value=current_tags, help="Edit memory tags"
        )

        # Metadata (read-only)
        with st.expander("📊 Metadata (Read-Only)"):
            col1, col2 = st.columns(2)

            with col1:
                st.text_input(
                    "Source", value=memory.get("source", "N/A"), disabled=True
                )
                st.text_input("Layer", value=memory.get("layer", "N/A"), disabled=True)

            with col2:
                if "timestamp" in memory:
                    st.text_input(
                        "Timestamp",
                        value=format_timestamp(memory["timestamp"]),
                        disabled=True,
                    )
                if "score" in memory:
                    st.text_input(
                        "Score", value=f"{memory['score']:.4f}", disabled=True
                    )

        st.divider()

        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            save_button = st.form_submit_button(
                "💾 Save Changes", type="primary", use_container_width=True
            )

        with col2:
            cancel_button = st.form_submit_button("❌ Cancel", use_container_width=True)

        with col3:
            delete_button = st.form_submit_button(
                "🗑️ Delete Memory", use_container_width=True
            )

    # Handle form submissions
    if save_button:
        if not new_content.strip():
            st.error("Content cannot be empty")
        else:
            try:
                with st.spinner("Saving changes..."):
                    # Parse tags
                    new_tags = [
                        tag.strip() for tag in new_tags_str.split(",") if tag.strip()
                    ]

                    # Update memory
                    success = client.update_memory(
                        memory_id=memory["id"], content=new_content, tags=new_tags
                    )

                    if success:
                        st.success("✓ Memory updated successfully!")
                        st.session_state.selected_memory = None
                        st.session_state.editor_mode = "search"

                        # Clear search results to force refresh
                        if "search_results" in st.session_state:
                            del st.session_state.search_results

                        st.balloons()

                        # Rerun after short delay
                        import time

                        time.sleep(1)
                        st.rerun()

            except Exception as e:
                st.error(f"Error updating memory: {e}")

    elif cancel_button:
        st.session_state.selected_memory = None
        st.session_state.editor_mode = "search"
        st.rerun()

    elif delete_button:
        st.warning("⚠️ Confirm deletion below")

        # Confirmation
        if st.button("⚠️ CONFIRM DELETE", type="secondary"):
            try:
                with st.spinner("Deleting memory..."):
                    success = client.delete_memory(memory["id"])

                    if success:
                        st.success("✓ Memory deleted successfully!")
                        st.session_state.selected_memory = None
                        st.session_state.editor_mode = "search"

                        # Clear search results
                        if "search_results" in st.session_state:
                            del st.session_state.search_results

                        # Rerun after short delay
                        import time

                        time.sleep(1)
                        st.rerun()

            except Exception as e:
                st.error(f"Error deleting memory: {e}")

# =============================================================================
# CREATE MODE
# =============================================================================
elif st.session_state.editor_mode == "create":
    st.header("➕ Create New Memory")

    # Create form
    with st.form("create_memory_form"):
        st.subheader("📝 New Memory Details")

        # Content
        content = st.text_area(
            "Content",
            placeholder="Enter memory content...",
            height=200,
            help="The main content of the memory",
        )

        # Layer selection
        layer = st.selectbox(
            "Memory Layer",
            options=["em", "wm", "sm", "ltm"],
            help="Select the memory layer for storage",
        )

        # Tags
        tags_str = st.text_input(
            "Tags (comma-separated)",
            placeholder="tag1, tag2, tag3",
            help="Add tags to categorize the memory",
        )

        # Source
        source = st.text_input(
            "Source",
            placeholder="dashboard-manual-entry",
            value="dashboard-manual-entry",
            help="Source identifier for the memory",
        )

        st.divider()

        # Action buttons
        col1, col2 = st.columns(2)

        with col1:
            create_button = st.form_submit_button(
                "💾 Create Memory", type="primary", use_container_width=True
            )

        with col2:
            cancel_button = st.form_submit_button("❌ Cancel", use_container_width=True)

    # Handle form submissions
    if create_button:
        if not content.strip():
            st.error("Content cannot be empty")
        else:
            try:
                with st.spinner("Creating memory..."):
                    # Parse tags
                    tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

                    # Create memory via store endpoint
                    response = client._request(
                        "POST",
                        "/v1/memory/store",
                        json={
                            "content": content,
                            "layer": layer,
                            "tags": tags,
                            "source": source,
                            "project": client.project_id,
                        },
                    )

                    st.success("✓ Memory created successfully!")
                    st.json(response)

                    st.session_state.editor_mode = "search"

                    # Clear search results
                    if "search_results" in st.session_state:
                        del st.session_state.search_results

                    st.balloons()

                    # Rerun after short delay
                    import time

                    time.sleep(1)
                    st.rerun()

            except Exception as e:
                st.error(f"Error creating memory: {e}")
                st.exception(e)

    elif cancel_button:
        st.session_state.editor_mode = "search"
        st.rerun()

st.divider()

# Help section
with st.expander("ℹ️ Help - Memory Editor"):
    st.markdown(
        """
    **Search Mode:**
    - Enter search terms to find memories
    - Use advanced filters to narrow results
    - Click "Edit" on any result to modify it

    **Edit Mode:**
    - Modify content and tags
    - Save changes or cancel
    - Delete memory if needed

    **Create Mode:**
    - Create new memories manually
    - Select appropriate layer
    - Add tags for organization

    **Tips:**
    - Use specific search terms for better results
    - Tags help organize and filter memories
    - Scores indicate relevance to search query
    - Always review before deleting
    """
    )

st.caption("RAE Memory Dashboard - Memory Editor")
