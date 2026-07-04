"""
Knowledge Graph Page - Graph Visualization

Explore knowledge graph relationships and entities.
"""

import os
import sys
import tempfile

import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.visualizations import apply_custom_css

# Apply styling
apply_custom_css()

# Page title
st.title("🕸️ Knowledge Graph")
st.markdown("Explore relationships and entities in the knowledge graph")

# Check connection
if "client" not in st.session_state or not st.session_state.get("connected", False):
    st.error("❌ Not connected to RAE API")
    st.info("👈 Please configure connection in the main page")
    st.stop()

client = st.session_state.client

st.divider()

# Configuration section
st.header("⚙️ Graph Settings")

col1, col2, col3 = st.columns(3)

with col1:
    physics_enabled = st.checkbox(
        "Enable Physics", value=True, help="Enable physics-based layout"
    )

with col2:
    node_size = st.slider(
        "Node Size", min_value=10, max_value=50, value=25, help="Size of graph nodes"
    )

with col3:
    edge_width = st.slider(
        "Edge Width", min_value=1, max_value=5, value=2, help="Width of graph edges"
    )

st.divider()

# Fetch graph data
st.header("📊 Knowledge Graph Visualization")

try:
    with st.spinner("Loading knowledge graph..."):
        graph_data = client.get_knowledge_graph()

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    if not nodes:
        st.warning("No graph data available")
        st.info(
            """
        **To populate the knowledge graph:**
        1. Store memories with relationships
        2. Use the reflection engine to extract entities
        3. Wait for graph extraction to complete

        The graph will automatically populate as you use RAE.
        """
        )
        st.stop()

    # Display statistics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Nodes", len(nodes))

    with col2:
        st.metric("Total Edges", len(edges))

    with col3:
        avg_connections = len(edges) / len(nodes) if nodes else 0
        st.metric("Avg Connections", f"{avg_connections:.2f}")

    st.divider()

    # Create network visualization
    net = Network(
        height="700px",
        width="100%",
        bgcolor="#0E1117",
        font_color="white",
        directed=True,
    )

    # Configure physics
    if physics_enabled:
        net.set_options(
            """
        {
          "physics": {
            "enabled": true,
            "barnesHut": {
              "gravitationalConstant": -8000,
              "centralGravity": 0.3,
              "springLength": 250,
              "springConstant": 0.001,
              "damping": 0.09,
              "avoidOverlap": 0.1
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "barnesHut",
            "timestep": 0.5,
            "stabilization": {
              "enabled": true,
              "iterations": 1000
            }
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "zoomView": true,
            "dragView": true
          }
        }
        """
        )
    else:
        net.set_options(
            """
        {
          "physics": {
            "enabled": false
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "zoomView": true,
            "dragView": true
          }
        }
        """
        )

    # Add nodes
    node_colors = {
        "entity": "#4ECDC4",
        "concept": "#45B7D1",
        "event": "#FF6B6B",
        "person": "#96CEB4",
        "project": "#FFD93D",
        "default": "#95E1D3",
    }

    for node in nodes:
        node_id = node.get("id") or node.get("node_id")
        label = node.get("label", node_id)
        node_type = node.get("type", "default")
        title = node.get("title", label)

        net.add_node(
            node_id,
            label=label,
            title=title,
            color=node_colors.get(node_type, node_colors["default"]),
            size=node_size,
        )

    # Add edges
    for edge in edges:
        source = edge.get("source") or edge.get("source_id")
        target = edge.get("target") or edge.get("target_id")
        relation = edge.get("relation", "")

        if source and target:
            net.add_edge(source, target, label=relation, width=edge_width, arrows="to")

    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".html") as f:
        net.save_graph(f.name)
        with open(f.name, "r") as file:
            html_content = file.read()

    # Display graph
    components.html(html_content, height=750, scrolling=True)

    st.caption(
        """
    **Interactive Graph:**
    - Click and drag nodes to reposition
    - Scroll to zoom
    - Hover over nodes and edges for details
    - Click nodes to highlight connections
    """
    )

except Exception as e:
    st.error(f"Error loading knowledge graph: {e}")
    st.exception(e)

st.divider()

# Graph analysis
st.header("📈 Graph Analysis")

if nodes and edges:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Node Distribution")

        # Count nodes by type
        node_types = {}
        for node in nodes:
            node_type = node.get("type", "default")
            node_types[node_type] = node_types.get(node_type, 0) + 1

        for node_type, count in sorted(
            node_types.items(), key=lambda x: x[1], reverse=True
        ):
            st.write(f"**{node_type.title()}:** {count}")

    with col2:
        st.subheader("Top Connected Nodes")

        # Count connections per node
        node_connections = {}
        for edge in edges:
            source = edge.get("source") or edge.get("source_id")
            target = edge.get("target") or edge.get("target_id")

            node_connections[source] = node_connections.get(source, 0) + 1
            node_connections[target] = node_connections.get(target, 0) + 1

        # Sort by connections
        top_nodes = sorted(node_connections.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        for node_id, connections in top_nodes:
            # Find node label
            node_label = node_id
            for node in nodes:
                if (node.get("id") or node.get("node_id")) == node_id:
                    node_label = node.get("label", node_id)
                    break

            st.write(f"**{node_label}:** {connections} connections")

st.divider()

# Relationship explorer
st.header("🔍 Relationship Explorer")

if nodes:
    # Select node
    node_options = {
        (node.get("id") or node.get("node_id")): node.get("label", node.get("id", ""))
        for node in nodes
    }

    selected_node = st.selectbox(
        "Select Node to Explore",
        options=list(node_options.keys()),
        format_func=lambda x: node_options[x],
    )

    if selected_node:
        # Find connected nodes
        connected_nodes = []
        for edge in edges:
            source = edge.get("source") or edge.get("source_id")
            target = edge.get("target") or edge.get("target_id")
            relation = edge.get("relation", "")

            if source == selected_node:
                # Find target node label
                target_label = target
                for node in nodes:
                    if (node.get("id") or node.get("node_id")) == target:
                        target_label = node.get("label", target)
                        break

                connected_nodes.append(
                    {
                        "type": "outgoing",
                        "relation": relation,
                        "node": target_label,
                        "node_id": target,
                    }
                )

            elif target == selected_node:
                # Find source node label
                source_label = source
                for node in nodes:
                    if (node.get("id") or node.get("node_id")) == source:
                        source_label = node.get("label", source)
                        break

                connected_nodes.append(
                    {
                        "type": "incoming",
                        "relation": relation,
                        "node": source_label,
                        "node_id": source,
                    }
                )

        if connected_nodes:
            st.success(f"Found {len(connected_nodes)} connections")

            # Group by type
            outgoing = [c for c in connected_nodes if c["type"] == "outgoing"]
            incoming = [c for c in connected_nodes if c["type"] == "incoming"]

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Outgoing Relationships")
                for conn in outgoing:
                    st.write(f"→ **{conn['relation']}** → {conn['node']}")

            with col2:
                st.subheader("Incoming Relationships")
                for conn in incoming:
                    st.write(f"← **{conn['relation']}** ← {conn['node']}")

        else:
            st.info("No connections found for this node")

st.divider()
st.caption("RAE Memory Dashboard - Knowledge Graph View")
