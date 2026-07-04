#!/usr/bin/env python3
"""
RAE Cluster Connection Utility
Usage: python scripts/connect_cluster.py

This script:
1. Verifies SSH connectivity to Compute Nodes (Node1, Node2).
2. Verifies HTTP connectivity to Inference Node (Node3).
3. Prints a status report and connection strings for MCP.
"""

import asyncio
import os

import httpx
import yaml

# Configuration paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "cluster.yaml")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ Config not found: {CONFIG_PATH}")
        return None
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


async def check_ssh_node(node_id, host, user):
    """Check SSH connectivity"""
    cmd = f"ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no -o BatchMode=yes {user}@{host} 'exit 0'"
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    await proc.wait()
    return proc.returncode == 0


async def check_http_node(node_id, url):
    """Check HTTP connectivity"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
            return resp.status_code == 200
    except Exception:
        return False


async def main():
    print("🔌 RAE Cluster Connector")
    print("=======================")

    config = load_config()
    if not config:
        return

    nodes = config.get("nodes", {})
    results = {}

    print(f"Checking {len(nodes)} nodes...")

    tasks = []
    for key, node in nodes.items():
        if node["transport"] == "ssh_mcp":
            tasks.append((key, node, check_ssh_node(key, node["host"], node["user"])))
        elif node["transport"] == "local_proxy":
            # For proxy, we check the target URL
            target_url = node.get("url")
            tasks.append((key, node, check_http_node(key, target_url)))

    # Run checks
    for key, node, coro in tasks:
        is_online = await coro
        results[key] = is_online
        status = "✅ ONLINE" if is_online else "❌ OFFLINE"
        print(f"[{node['id'].upper()}] {key}: {status}")
        if is_online and node["transport"] == "local_proxy":
            print(f"   ℹ️  Proxy Script: {node['proxy_script']}")
            print(f"   ℹ️  Target: {node['url']}")

    print("\n💡 Usage Instructions:")
    print("   - Node1/2: Use MCP via SSH (Stdio)")
    print(
        "   - Node3: Run proxy locally: `python infra/node_agent/ollama_proxy_mcp.py`"
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
