# RAE Control Node API & Node1 Integration Plan

**Objective:** Enable distributed compute by implementing a Control Plane API in RAE and connecting the first remote node (`node1`/`KUBUS`).

## 1. Database Schema (PostgreSQL)
Create a new migration script `alembic/versions/xxxx_add_control_plane.py` to add:

### Table: `compute_nodes`
| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | UUID | PK |
| `node_id` | String | Unique (e.g., `kubus-gpu-01`) |
| `api_key_hash` | String | For auth |
| `status` | Enum | `ONLINE`, `OFFLINE`, `BUSY` |
| `last_heartbeat` | Timestamp | For liveness check |
| `capabilities` | JSONB | e.g., `{"gpu": "RTX4080", "vram": 16}` |
| `ip_address` | String | Tailscale IP (audit) |

### Table: `delegated_tasks`
| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | UUID | PK |
| `type` | String | e.g., `embedding_generation`, `llm_inference` |
| `status` | Enum | `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |
| `priority` | Integer | Default 0 |
| `payload` | JSONB | Task inputs |
| `result` | JSONB | Task outputs |
| `assigned_node_id`| UUID | FK to `compute_nodes` |
| `created_at` | Timestamp | |
| `started_at` | Timestamp | |
| `completed_at` | Timestamp | |

## 2. Backend Implementation (`apps/memory_api`)

### Models
- Create `apps/memory_api/models/control_plane.py` (SQLAlchemy models).
- Create Pydantic schemas in `apps/memory_api/schemas/control_plane.py`.

### Repositories
- `apps/memory_api/repositories/node_repository.py`: CRUD for nodes, heartbeat updates.
- `apps/memory_api/repositories/task_repository.py`: Queue management (claim task, submit result).

### Service Layer
- `apps/memory_api/services/control_plane_service.py`:
  - `register_node()`: Validate & store node.
  - `process_heartbeat()`: Update timestamp, mark offline if stale.
  - `poll_task()`: Atomic transaction to find pending task -> assign to node -> set status PROCESSING.

### API Routes
- `apps/memory_api/routes/control_plane.py`:
  - `POST /control/nodes/register`
  - `POST /control/nodes/heartbeat`
  - `GET /control/tasks/poll`
  - `POST /control/tasks/{task_id}/result`

## 3. Node Agent (Client Side)
Create a lightweight Python agent to run on `node1`.
- Location: `infra/node_agent/`
- **Features:**
  - Auto-registration on startup.
  - 30s Heartbeat loop.
  - Task polling loop (when idle).
  - Local executor (initially just a "no-op" or simple echo).

## 4. Execution Steps

1.  **Schema**: Generate & apply Alembic migration.
2.  **Backend**: Implement Models, Repositories, Service, Routes.
3.  **Test**: Add unit tests for `ControlPlaneService`.
4.  **Client**: Implement `infra/node_agent/main.py`.
5.  **Integration**: Run agent locally, verify registration and task claiming via API.
6.  **Deploy**: Copy agent to `node1`, configure systemd, verify remote connection.

## 5. Success Criteria
- [ ] `node1` appears in `compute_nodes` table with `status=ONLINE`.
- [ ] Heartbeat updates `last_heartbeat` every 30s.
- [ ] `node1` can pull a test task and write the result back to DB.
