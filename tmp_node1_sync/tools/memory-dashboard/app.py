"""
RAE Memory Dashboard - Main Application

Enterprise-grade Streamlit dashboard for RAE Memory Engine.
Provides visualization and management of agent memories.

Features:
- Real-time memory statistics
- Timeline visualization
- Knowledge graph explorer
- Memory editor
- Query inspector
"""

import os
import time

import streamlit as st
from utils.api_client import RAEClient, get_cached_stats
from utils.visualizations import (
    apply_custom_css,
    create_layer_distribution_chart,
    create_tags_wordcloud_chart,
)

# Page configuration
st.set_page_config(
    page_title="RAE Memory Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://docs.rae-memory.dev",
        "Report a bug": "https://github.com/your-org/rae-agentic-memory/issues",
        "About": "RAE Memory Dashboard v1.0.0 - Enterprise Memory Management",
    },
)

# Apply custom styling
apply_custom_css()

# Title and description
st.title("🧠 RAE Memory Dashboard")
st.markdown(
    """
Enterprise-grade dashboard for visualizing and managing your AI agent's memory.

**Features:**
- 📊 Real-time statistics and analytics
- 📅 Timeline visualization
- 🕸️ Knowledge graph explorer
- ✏️ Memory editor
- 🔍 Query inspector
"""
)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # Initialize session state for config if not exists
    if "config" not in st.session_state:
        st.session_state.config = {
            "api_url": os.getenv("RAE_API_URL", "http://localhost:8001"),
            "api_key": os.getenv("RAE_API_KEY", "default-key"),
            # Default to the tenant with actual data found in DB
            "tenant_id": os.getenv(
                "RAE_TENANT_ID", "00000000-0000-0000-0000-000000000000"
            ),
            "project_id": os.getenv("RAE_PROJECT_ID", "benchmark_project"),
        }

    # Connection settings
    with st.expander("API Connection", expanded=True):
        api_url = st.text_input(
            "API URL",
            value=st.session_state.config["api_url"],
            help="URL of the RAE Memory API",
        )

        api_key = st.text_input(
            "API Key",
            value=st.session_state.config["api_key"],
            type="password",
            help="API authentication key",
        )

        # Dynamic Tenant Loading
        tenants_data = []  # List of dicts
        tenants_options = []  # What to pass to selectbox

        if api_url and api_key:
            try:
                temp_client = RAEClient(
                    api_url=api_url,
                    api_key=api_key,
                    tenant_id="system-discovery",
                    timeout=5.0,
                )
                # fetch dicts {id, name}
                tenants_data = temp_client.get_tenants()
                # Ensure compatibility if API returns old list of strings
                if tenants_data and isinstance(tenants_data[0], str):
                    tenants_data = [{"id": t, "name": "Unknown"} for t in tenants_data]

                # Sort by name
                tenants_data.sort(key=lambda x: x.get("name", ""))
                tenants_options = [t["id"] for t in tenants_data]

            except Exception:
                pass

        if tenants_options:
            # Helper to find name by ID
            def get_tenant_name(tid):
                for t in tenants_data:
                    if t["id"] == tid:
                        # Use first 8 chars of ID if name is generic "Unknown"
                        name = t["name"]
                        if name == "Unknown":
                            return f"{tid[:8]}... (Default)"
                        return f"{name} ({tid[:8]}...)"
                return tid

            # Current selection index
            current_tid = st.session_state.config["tenant_id"]
            try:
                default_idx = tenants_options.index(current_tid)
            except ValueError:
                default_idx = 0

            selected_tenant_id = st.selectbox(
                "Tenant",
                options=tenants_options,
                index=default_idx,
                format_func=get_tenant_name,
                help="Select Workspace/Tenant",
            )
        else:
            selected_tenant_id = st.text_input(
                "Tenant ID",
                value=st.session_state.config["tenant_id"],
                help="Tenant identifier for multi-tenancy",
            )

        # Dynamic Project Loading (Needs selected tenant)
        projects_list = []
        if api_url and api_key and selected_tenant_id:
            try:
                # Need to init client with new tenant to fetch projects
                temp_client_proj = RAEClient(
                    api_url=api_url,
                    api_key=api_key,
                    tenant_id=selected_tenant_id,
                    timeout=5.0,
                )
                projects_list = sorted(temp_client_proj.get_projects())
            except Exception:
                pass

        if projects_list:
            try:
                default_pid_idx = projects_list.index(
                    st.session_state.config["project_id"]
                )
            except ValueError:
                default_pid_idx = 0

            selected_project_id = st.selectbox(
                "Project",
                options=projects_list,
                index=default_pid_idx,
            )
        else:
            selected_project_id = st.text_input(
                "Project ID",
                value=st.session_state.config["project_id"],
            )

        # AUTO-UPDATE LOGIC
        # If selection changed, update config and client immediately
        if (
            selected_tenant_id != st.session_state.config["tenant_id"]
            or selected_project_id != st.session_state.config["project_id"]
            or api_url != st.session_state.config["api_url"]
        ):

            st.session_state.config.update(
                {
                    "api_url": api_url,
                    "api_key": api_key,
                    "tenant_id": selected_tenant_id,
                    "project_id": selected_project_id,
                }
            )

            # Re-init client
            new_client = RAEClient(
                api_url=api_url,
                api_key=api_key,
                tenant_id=selected_tenant_id,
                project_id=selected_project_id,
            )

            if new_client.test_connection():
                st.session_state.client = new_client
                st.session_state.connected = True
                st.rerun()  # Refresh page with new data
            else:
                st.error("Connection failed with new settings")

    # Tenant Settings (Renaming)
    if st.session_state.get("connected", False) and selected_tenant_id:
        with st.expander("⚙️ Tenant Settings"):
            new_tenant_name = st.text_input("Rename Tenant", placeholder="New name...")
            if st.button("Update Name"):
                if new_tenant_name:
                    success = st.session_state.client.update_tenant_name(
                        selected_tenant_id, new_tenant_name
                    )
                    if success:
                        st.success("Renamed! Refreshing...")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Enter a name first")

    # Project Settings (Renaming)
    if st.session_state.get("connected", False) and selected_project_id:
        with st.expander("📁 Project Settings"):
            new_project_name = st.text_input(
                "Rename Project", placeholder="New name..."
            )
            if st.button("Update Project Name"):
                if new_project_name:
                    success = st.session_state.client.rename_project(
                        selected_project_id, new_project_name
                    )
                    if success:
                        st.session_state.config["project_id"] = new_project_name
                        st.success("Project Renamed! Refreshing...")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Enter a name first")

    # Auto-Refresh Logic
    with st.expander("⏱️ Auto-Refresh", expanded=False):
        auto_refresh = st.checkbox("Enable Auto-Refresh", value=False)
        refresh_rate = st.slider(
            "Refresh Rate (seconds)", min_value=1, max_value=60, value=5
        )

        if auto_refresh:
            st.caption(f"Refreshing every {refresh_rate}s...")
            st.caption("Backend WebSocket broadcasting is enabled for real-time consumers.")
            time.sleep(refresh_rate)
            st.rerun()

    # Status Indicator (Thinking Bar)
    # Mocking task status for now until backend supports /tasks/active
    # In real impl, we would call client.get_active_tasks()
    if st.sidebar.button("🚀 Rebuild Reflection"):
        with st.spinner("Dispatching to Node1..."):
            # Call API trigger logic here (simplified)
            pass
        st.sidebar.success("Task dispatched! Monitor logs.")

    # Connection status (Compact)
    if st.session_state.get("connected", False):
        st.sidebar.success(f"Connected: {st.session_state.config['project_id']}")
    else:
        st.sidebar.warning("🔴 Not connected")

    # Help section
    with st.expander("ℹ️ Help"):
        st.markdown(
            """
        **Quick Start:**
        1. Configure connection settings
        2. Click "Connect"
        3. Navigate to pages in sidebar

        **Pages:**
        - **Timeline**: View memory timeline
        - **Knowledge Graph**: Explore relationships
        - **Memory Editor**: Edit memories
        - **Query Inspector**: Test queries

        **Troubleshooting:**
        - Ensure RAE API is running
        - Check API URL and credentials
        - Click "Refresh" to reload data
        """
        )

# Main content area
if "connected" in st.session_state and st.session_state.connected:
    client = st.session_state.client

    st.divider()

    # Overview section
    st.header("📊 Overview")

    # Fetch statistics
    try:
        stats = get_cached_stats(client, client.tenant_id, client.project_id)

        # Metrics row
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "Total Memories",
                stats.get("total", 0),
                help="Total number of memories stored",
            )

        with col2:
            st.metric(
                "Episodic", stats.get("episodic", 0), help="Recent event memories"
            )

        with col3:
            st.metric(
                "Working", stats.get("working", 0), help="Current context memories"
            )

        with col4:
            st.metric(
                "Semantic",
                stats.get("semantic", 0),
                help="Concept and guideline memories",
            )

        with col5:
            st.metric(
                "Long-term", stats.get("ltm", 0), help="Consolidated long-term memories"
            )

    except Exception as e:
        st.error(f"Error fetching statistics: {e}")

    st.divider()

    # Quick visualizations
    st.header("📈 Quick Analytics")

    tab1, tab2, tab3 = st.tabs(["Recent Activity", "Layer Distribution", "Top Tags"])

    with tab1:
        try:
            recent_memories = client.get_memories(limit=50)

            if recent_memories:
                st.subheader("Recent Memory Activity")
                st.caption(f"Showing last {len(recent_memories)} memories")

                # Display recent memories
                for memory in recent_memories[:10]:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])

                        with col1:
                            content = memory.get("content", "")
                            if len(content) > 100:
                                content = content[:100] + "..."
                            st.text(content)

                        with col2:
                            st.caption(memory.get("layer", "N/A"))

                        with col3:
                            if "timestamp" in memory:
                                st.caption(memory["timestamp"][:10])

                        st.divider()
            else:
                st.info("No recent memories found")

        except Exception as e:
            st.error(f"Error fetching recent memories: {e}")

    with tab2:
        try:
            memories = client.get_memories(limit=100)

            if memories:
                fig = create_layer_distribution_chart(memories)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available for visualization")

        except Exception as e:
            st.error(f"Error creating chart: {e}")

    with tab3:
        try:
            memories = client.get_memories(limit=100)

            if memories:
                fig = create_tags_wordcloud_chart(memories)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No tags found")

        except Exception as e:
            st.error(f"Error creating tag chart: {e}")

    st.divider()

    # Project reflection
    st.header("🔮 Project Reflection")

    with st.expander("View Current Project Reflection"):
        try:
            with st.spinner("Generating reflection..."):
                reflection = client.get_reflection()
                st.markdown(reflection)
        except Exception as e:
            st.error(f"Error fetching reflection: {e}")

    # Footer
    st.divider()
    st.caption("RAE Memory Dashboard v1.0.0 | Enterprise Memory Management")

else:
    # Not connected - show welcome message
    st.info(
        "👈 Please configure connection settings in the sidebar and click 'Connect'"
    )

    st.divider()

    # Welcome content
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🚀 Getting Started")
        st.markdown(
            """
        1. **Start RAE API**
           ```bash
           docker compose up -d
           ```

        2. **Configure Connection**
           - Enter API URL (default: http://localhost:8000)
           - Set API key and tenant ID
           - Click "Connect"

        3. **Explore Dashboard**
           - View timeline
           - Explore knowledge graph
           - Edit memories
           - Test queries
        """
        )

    with col2:
        st.subheader("📚 Features")
        st.markdown(
            """
        **Timeline Visualization**
        - View memory history
        - Filter by layer and date
        - Interactive charts

        **Knowledge Graph**
        - Explore relationships
        - Visual network graph
        - Node and edge details

        **Memory Editor**
        - Search and edit memories
        - Update content and tags
        - Delete memories

        **Query Inspector**
        - Test search queries
        - View ranked results
        - Inspect scoring
        """
        )

    st.divider()

    # Example connection
    st.subheader("💡 Example Configuration")

    st.code(
        """
API URL: http://localhost:8000
API Key: your-api-key
Tenant ID: default-tenant
Project ID: my-project
    """,
        language="text",
    )

    st.caption("Ensure RAE Memory API is running and accessible at the specified URL.")
