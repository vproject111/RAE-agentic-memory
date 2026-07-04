# RAE – Single-Node Production Deployment Guide

This document describes a **reference production setup** for RAE-agentic-memory on a **single Linux server**.

> ⚠️ **Important disclaimer**  
> This guide is a *reference example*.  
> Real-world production deployments MUST be adapted to your infrastructure, security policies, compliance requirements (e.g. ISO/IEC 42001, GDPR), and risk profile.  
> It is **not** a certified, one-size-fits-all production recipe.

---

## 1. Architecture overview (single node)

On a single node, all components run on the same physical/virtual machine:

- **PostgreSQL** – system-of-record (tenants, users, auth, budgets, audit log, risk register, policies, etc.)
- **Vector store** – e.g. Qdrant or PostgreSQL with pgvector (semantic memory)
- **Redis** – cache / task coordination / fast ephemeral data (if used)
- **RAE API service** – main backend (FastAPI or similar)
- **Workers / background tasks** – decay, summarization, dreaming, enrichment, etc.
- **Dashboard / UI** – optional web frontend for monitoring and admin
- **Reverse proxy** (nginx / Traefik / Caddy) – TLS termination, routing, maybe rate limiting

All run either:

- as **Docker containers** (recommended for consistency), or  
- as systemd services (for advanced users who prefer native installs).

---

## 2. Recommended server baseline

Minimal **production** baseline (adapt to your workload):

- **4–8 vCPUs**
- **16–32 GB RAM** (64 GB+ required if running Local LLMs/Ollama)
- **Fast SSD storage**, with separate volumes for:
  - PostgreSQL data
  - vector store data
- **64-bit Linux** (e.g. Ubuntu Server LTS, Debian, etc.)
- Regular automated backups (database + vector store + configuration)

---

## 3. Deployment steps (high level)

### 3.1. Prepare the OS and user

- Create a dedicated system user, e.g. `rae`.
- Configure SSH access and disable password login.
- Keep the system updated.

### 3.2. Install Docker and Docker Compose

Follow official Docker documentation for your OS. Add the `rae` user to the docker group.

### 3.3. Prepare environment configuration

On the server, clone the repository:

```bash
sudo -iu rae
git clone https://github.com/dreamsoft-pro/RAE-agentic-memory.git
cd RAE-agentic-memory
cp .env.example .env
```

Prepare the `.env` file.

**Privacy-First Mode (Optional):**
If your deployment requires that **no data leaves the server** (e.g., strictly internal processing), configure RAE to use a local LLM backend.

1.  Install Ollama or vLLM on the host or as a sidecar container.
2.  Set `RAE_LLM_BACKEND=ollama`.
3.  Set `OLLAMA_API_URL=http://localhost:11434`.
4.  Ensure your server has sufficient GPU/RAM resources.

**Standard Mode (Cloud LLM):**
Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`.

### 3.4. Start production stack (single-node)

Use a dedicated production compose file (e.g. docker compose.prod.yml) if the repo provides one.

```bash
docker compose up -d
```

### 3.5. Run database migrations

The system is configured to run migrations automatically on startup. If needed, you can verify or run them manually:

```bash
docker compose exec rae-api alembic upgrade head
```

### 3.6. Expose via reverse proxy (HTTPS)

Use nginx, Traefik or Caddy in front of the stack to terminate TLS.

Example nginx snippet:

```nginx
server {
    listen 443 ssl;
    server_name rae.example.com;
    # ... SSL config ...

    location / {
        proxy_pass http://127.0.0.1:8000; # RAE API
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 4. Backups, monitoring and logs

### 4.1. Backups
- **PostgreSQL**: nightly `pg_dump` to external storage.
- **Vector DB**: verify vendor’s recommended backup strategy (Qdrant snapshots).
- **Configuration**: `.env`, deployment files.

### 4.2. Monitoring & metrics
Integrate system metrics (CPU, RAM) and RAE application metrics (Prometheus exposed at `/metrics`) with Grafana.

### 4.3. Logs
Route logs from containers to centralized log storage (ELK, Loki) or systemd journal.

---

## 5. Security and compliance notes

- Enable and test **PostgreSQL Row-Level Security (RLS)** for multi-tenancy.
- Secure all external endpoints with TLS and authentication.
- Restrict network access to database / vector / Redis to trusted hosts only (firewall).
- Periodically review Audit Logs and Data Retention policies.

---

## 6. When to move beyond single-node

Consider a clustered / HA setup (e.g. Proxmox or Kubernetes) if:
- RAE becomes critical infrastructure.
- You have strict uptime requirements.
- You need to scale compute (e.g., multiple LLM inference nodes) independently of storage.

See `PRODUCTION_PROXMOX_HA.md` for HA deployment.