# RAE – Proxmox HA Cluster Deployment (Reference Guide)

This document describes a **reference high-availability deployment** of RAE-agentic-memory on a **Proxmox cluster (≥ 3 nodes)**.

It reflects a realistic “enterprise-style” setup where:
- Proxmox provides VM orchestration, HA and storage.
- RAE components are split across separate VMs.
- The system can survive single-node failures.

> ⚠️ **Important disclaimer**  
> This is a **reference architecture**, not a certified blueprint.  
> You MUST adapt it to your own Proxmox cluster layout, storage configuration, network topology, security and compliance requirements.

---

## 1. Target architecture on Proxmox

Assume a **3-node Proxmox cluster** with shared or replicated storage (e.g. Ceph, ZFS replication).

Recommended VM layout (example):

1. **VM: RAE-DB**
   - PostgreSQL (with RLS enabled)
   - Allocated resources: e.g. 4 vCPU, 16 GB RAM, fast SSD storage (Ceph/NVMe).

2. **VM: RAE-VECTOR**
   - Qdrant or another vector database.
   - 4 vCPU, 8–16 GB RAM, SSD.

3. **VM: RAE-REDIS**
   - Redis for cache / task coordination.
   - 2–4 vCPU, 8 GB RAM.

4. **VM: RAE-API**
   - RAE API backend + workers.
   - 4–8 vCPU, 16–32 GB RAM.
   - Stateless, can be scaled horizontally (multiple VMs behind LB).

5. **VM: RAE-LLM (Optional - Local Privacy)**
   - Local Inference Server (Ollama / vLLM / TGI).
   - Required if running "Local First" without cloud APIs.
   - **Hardware**: GPU Passthrough (NVIDIA A100/A10/L4) highly recommended.
   - Resources: 8-16 vCPU, 32GB+ RAM (if CPU-only inference).

6. **VM: RAE-DASHBOARD / GATEWAY**
   - Dashboard / UI.
   - Reverse proxy (nginx / Traefik / Caddy) for TLS termination.

---

## 2. Proxmox-level HA considerations

### 2.1. Storage
- Use highly available storage (Ceph, ZFS replication).
- Place VM disks for Postgres and vector DB on the most reliable storage class.

### 2.2. HA and failover
- Configure **HA groups** in Proxmox for critical VMs (`RAE-DB`, `RAE-API`).
- Set appropriate restart priorities and timeouts.

### 2.3. Networking
- Use internal VLANs/SDN for database traffic (db <-> api).
- Only expose the Gateway VM to the public network.

---

## 3. Installing RAE components on VMs

### 3.1. RAE-DB VM (PostgreSQL)
- Install PostgreSQL + pgvector.
- Configure `max_connections`, memory (`shared_buffers`).
- Harden access: only allow connections from `RAE-API` VMs.

### 3.2. RAE-VECTOR VM
- Install Qdrant.
- Bind to internal IP.
- Configure snapshots backup to external storage (Proxmox Backup Server).

### 3.3. RAE-API VM
- Deploy RAE code (Git + Docker).
- Configure `.env`:
  - `DATABASE_URL` → RAE-DB VM internal IP.
  - `QDRANT_URL` → RAE-VECTOR VM internal IP.
  - `OLLAMA_API_URL` → RAE-LLM VM internal IP (if using local LLM).

### 3.4. RAE-LLM VM (Local Inference)
- Install **Ollama** or **vLLM**.
- Pull required models (e.g. `llama3`, `mistral`).
- Expose API on internal network only.
- Ensure GPU drivers are correctly installed if using passthrough.

---

## 4. Environment configuration for clustered setup

Use environment variables to reflect the clustered layout:

```env
DATABASE_URL=postgresql://rae_user:password@rae-db.internal:5432/rae
QDRANT_HOST=rae-vector.internal
QDRANT_PORT=6333
REDIS_URL=redis://rae-redis.internal:6379/0

# For Local First / Privacy setup:
RAE_LLM_BACKEND=ollama
OLLAMA_API_URL=http://rae-llm.internal:11434
```

---

## 5. Backups and Upgrades

- **Backups**: Use **Proxmox Backup Server (PBS)** for full VM snapshots. Combine with logical dumps (`pg_dump`).
- **Upgrades**: Use "Blue-Green" deployment for `RAE-API` VMs (spin up new version, switch traffic, shut down old).

---

## 6. Summary

A Proxmox-based HA deployment allows RAE to scale for enterprise workloads while maintaining data sovereignty.
By adding a dedicated `RAE-LLM` node with GPU resources, you achieve a fully private, high-performance cognitive architecture without relying on external AI providers.