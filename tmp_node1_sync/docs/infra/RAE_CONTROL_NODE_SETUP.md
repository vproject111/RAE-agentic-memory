RAE_CONTROL_NODE_SETUP.md

(u Ciebie – RAE + control plane)

# RAE Control Node – Setup Guide

This document describes how to set up the CENTRAL RAE CONTROL NODE.
This machine:
- has a static public IP
- hosts RAE (memory + control plane)
- manages task scheduling for remote compute nodes
- NEVER executes heavy compute tasks itself

---

## 1. Assumptions

- Linux (Ubuntu 22.04+ recommended)
- Docker + docker compose available
- Static public IP
- No GPU required
- This node is ALWAYS ON

---

## 2. Network – Tailscale (Required)

### Install Tailscale
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

Verify
tailscale status


Note your Tailscale IP (100.x.x.x).

3. RAE Network Binding (Critical)

RAE services MUST:

bind ONLY to Tailscale interface

NOT expose APIs on public IP

Example:

RAE_BIND_ADDRESS=100.x.x.x
RAE_PORT=8080


Firewall:

allow Tailscale

block public ingress

4. Components Running on Control Node
Mandatory

RAE core

Memory databases

Node Registry

Task Queue

Must NOT run here

LLM inference

GPU workloads

Code execution agents

5. Node Registry API (Minimal Contract)

RAE must expose the following endpoints:

POST /nodes/register
POST /nodes/heartbeat
GET  /tasks/poll
POST /tasks/result


All endpoints:

accessible ONLY via Tailscale

authenticated via node token

6. Heartbeat Policy (Strict)

Heartbeat interval: 30 seconds

Timeout: 120 seconds

No heartbeat = node OFFLINE

OFFLINE nodes MUST NOT receive tasks

No exceptions.

7. Task Queue Rules

Each task MUST:

be idempotent

have a unique task_id

be safely re-queued if a node disappears

RAE is the SINGLE source of truth for:

task state

task history

results

8. Security Rules (Non-Negotiable)

Nodes have NO DB access

Nodes receive ONLY task-scoped data

No shared filesystem

No persistent credentials on nodes

9. Verification Checklist

RAE listens only on Tailscale IP

Nodes cannot reach DB ports

Node without heartbeat is invisible

Tasks re-queue correctly

RAE can be stopped without affecting nodes

10. Definition of Done

The control node is correctly set up when:

remote nodes can register

tasks are pulled (not pushed)

node availability is dynamic

RAE memory remains authoritative


---

# 📄 PLIK 2  
## `RAE_COMPUTE_NODE_SETUP.md`  
*(Kubuś, Julka – GPU node’y)*

```md
# RAE Compute Node – Setup Guide

This document describes how to set up a TEMPORARY GPU COMPUTE NODE.
This node:
- may appear and disappear at any time
- executes tasks assigned by RAE
- NEVER stores memory
- NEVER accesses databases

---

## 1. Assumptions

- Linux (Ubuntu 22.04+)
- NVIDIA GPU (RTX 4080 or similar)
- Docker installed
- User is NOT always present

---

## 2. System Preparation

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose-plugin -y
sudo usermod -aG docker $USER


Log out / log in.

3. Network – Tailscale (Required)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up


Verify:

tailscale status


Node must be visible to RAE control node.

4. Directory Layout
/opt/rae-node/
├── agent/
│   ├── main.py
│   ├── executor.py
│   ├── capabilities.py
│   └── config.yaml
├── models/
├── workdir/
└── logs/

5. Node Configuration (config.yaml)
Example: Kubuś
node_id: kubus-gpu-01
trusted: true

capabilities:
  gpu: true
  gpu_model: RTX_4080
  vram_gb: 16
  ram_gb: 64
  llm:
    - python-specialist
    - code-refactor

heartbeat_interval_sec: 30
rae_endpoint: http://100.x.x.x:8080

Example: Julka
node_id: julka-gpu-01
trusted: false

capabilities:
  gpu: true
  gpu_model: RTX_4080
  vram_gb: 16
  ram_gb: 64
  llm:
    - python-specialist

heartbeat_interval_sec: 30
rae_endpoint: http://100.x.x.x:8080

6. Local LLM (Required)
Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

Pull model
ollama pull deepseek-coder:33b


Ollama MUST be local.
No cloud calls allowed.

7. Node Agent Runtime Rules

The node agent:

sends heartbeat every 30s

pulls tasks (never receives push)

executes tasks in /workdir

deletes all data after task completion

If agent stops → node disappears.

8. systemd Service (Recommended)

Create:

/etc/systemd/system/rae-node.service

[Unit]
Description=RAE Compute Node Agent
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/rae-node/agent/main.py
Restart=always
User=rae-node

[Install]
WantedBy=multi-user.target


Enable:

sudo systemctl daemon-reload
sudo systemctl enable rae-node
sudo systemctl start rae-node

9. Security Rules (Strict)

Node has NO access to RAE DB

Node has NO long-term memory

Node is safe to turn off anytime

No secrets stored outside config

10. Definition of Done

The compute node is ready when:

it appears in RAE registry

it sends regular heartbeat

it pulls tasks only when idle

it can disappear without consequences


---

## ✅ Co dalej (bardzo krótko)

Następny naturalny krok (jak będziesz chciał):
1. **plik 3** – `RAE_NODE_AGENT_PROTOCOL.md` (JSON kontrakt)
2. **plik 4** – `RAE_COMPUTE_MESH_OVERVIEW.md` (1-stronicowy diagram)
3. **gotowy skeleton node-agent (Python)**

Ale **to, co masz powyżej, wystarczy żeby realnie ruszyć**.

Jeśli chcesz, w kolejnym kroku mogę:
- skleić to w **jedno repo infra**
- albo przygotować **prompt dla Gemini: „zaimplementuj dokładnie to”**

Masz bardzo solidny fundament.