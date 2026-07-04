"""
RAE Context Watcher - HTTP API Server

A local daemon that watches project files and feeds them into the RAE Memory Engine.
This is NOT the Model Context Protocol server - this is an HTTP-based file watcher.

For MCP (IDE integration), see integrations/mcp/
"""

import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from prometheus_client import Counter, Gauge, Histogram
from pydantic import BaseModel

from .rae_client import RAEClient
from .watcher import start_watching

# Prometheus Metrics
FILES_SYNCED = Counter("files_synced_total", "Total files synced to RAE", ["tenant_id"])
FILE_SYNC_ERRORS = Counter(
    "file_sync_errors_total", "Total file sync errors", ["tenant_id", "error_type"]
)
FILE_SYNC_DURATION = Histogram(
    "file_sync_duration_seconds", "File sync duration in seconds", ["tenant_id"]
)
WATCHED_PROJECTS = Gauge(
    "watched_projects_total", "Number of currently watched projects"
)


# --- Application Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # Startup: Initialize resources
    app.state.watched_projects = {}
    print("Context Watcher starting up...")
    yield
    # Shutdown: Cleanup resources
    print("Context Watcher shutting down...")
    for project_id, project_data in app.state.watched_projects.items():
        if project_data.get("observer"):
            project_data["observer"].stop()
            project_data["observer"].join()
            print(f"Stopped watcher for project: {project_id}")


app = FastAPI(
    title="RAE Context Watcher",
    description="HTTP daemon that watches project files and feeds them into the RAE Memory Engine.",
    version="1.0.0",
    lifespan=lifespan,
)


# --- API Models ---
class Project(BaseModel):
    """Project registration request."""

    path: str
    tenant_id: str  # Each project should have its own tenant_id


class ProjectRegistrationResponse(BaseModel):
    """Project registration response."""

    project_id: str
    message: str


class StoreMemoryRequest(BaseModel):
    """Memory storage request."""

    content: str
    source: str
    layer: str = "ltm"
    tags: list = []
    project: str


class QueryMemoryRequest(BaseModel):
    """Memory query request."""

    query_text: str
    k: int = 10


class DeleteMemoryRequest(BaseModel):
    """Memory deletion request."""

    memory_id: str


# --- Helper Functions ---
def get_file_update_callback(tenant_id: str):
    """
    Creates a callback function for the file watcher.
    The callback will instantiate a RAEClient and store the file content.

    Args:
        tenant_id: The tenant ID for RAE API

    Returns:
        Callback function that handles file changes
    """

    def callback(file_path: str):
        start_time = time.time()
        print(f"File change detected for tenant {tenant_id}: {file_path}")

        try:
            rae_client = RAEClient(tenant_id=tenant_id)
            rae_client.store_file_memory(file_path)
            FILES_SYNCED.labels(tenant_id=tenant_id).inc()
        except Exception as e:
            FILE_SYNC_ERRORS.labels(
                tenant_id=tenant_id, error_type=type(e).__name__
            ).inc()
            print(f"Error syncing file {file_path}: {e}")
        finally:
            duration = time.time() - start_time
            FILE_SYNC_DURATION.labels(tenant_id=tenant_id).observe(duration)

    return callback


# --- API Endpoints ---


@app.get("/status")
async def get_status():
    """
    Returns the current status of the Context Watcher.

    Returns:
        Status information including watched project count
    """
    project_count = len(app.state.watched_projects)
    return {"status": "running", "watched_projects_count": project_count}


@app.post("/projects", response_model=ProjectRegistrationResponse)
async def register_project(project: Project, background_tasks: BackgroundTasks):
    """
    Registers a new project directory to be watched.

    Args:
        project: Project configuration (path and tenant_id)
        background_tasks: FastAPI background tasks

    Returns:
        Registration response with project ID
    """
    path = os.path.abspath(project.path)
    if not os.path.isdir(path):
        raise HTTPException(
            status_code=400, detail="The provided path is not a valid directory."
        )

    project_id = f"{project.tenant_id}-{os.path.basename(path)}"
    if project_id in app.state.watched_projects:
        raise HTTPException(
            status_code=400, detail=f"Project '{project_id}' is already being watched."
        )

    callback = get_file_update_callback(tenant_id=project.tenant_id)
    observer = start_watching(path, callback)

    app.state.watched_projects[project_id] = {
        "path": path,
        "tenant_id": project.tenant_id,
        "observer": observer,
    }

    # Update metrics
    WATCHED_PROJECTS.set(len(app.state.watched_projects))

    print(f"Started watching project: {project_id} at {path}")

    return ProjectRegistrationResponse(
        project_id=project_id, message=f"Started watching project '{project_id}'."
    )


@app.get("/projects")
async def list_projects():
    """
    Lists all projects currently being watched.

    Returns:
        Dictionary of watched projects with their metadata
    """
    # Return a serializable version of the watched_projects dict
    return {
        pid: {"path": data["path"], "tenant_id": data["tenant_id"]}
        for pid, data in app.state.watched_projects.items()
    }


@app.delete("/projects/{project_id}")
async def unregister_project(project_id: str):
    """
    Stops watching a project directory.

    Args:
        project_id: The project ID to unregister

    Returns:
        Success message
    """
    if project_id not in app.state.watched_projects:
        raise HTTPException(status_code=404, detail="Project not found.")

    project_data = app.state.watched_projects[project_id]
    observer = project_data.get("observer")
    if observer:
        observer.stop()
        observer.join()

    del app.state.watched_projects[project_id]

    # Update metrics
    WATCHED_PROJECTS.set(len(app.state.watched_projects))

    print(f"Stopped watching project: {project_id}")

    return {"message": f"Stopped watching project '{project_id}'."}


# --- RAE API Proxy Endpoints ---


@app.post("/memory/store")
async def store_memory_proxy(req: StoreMemoryRequest, tenant_id: str):
    """
    Proxy endpoint to store memory in the RAE API.

    Args:
        req: Memory storage request
        tenant_id: Tenant ID for RAE API

    Returns:
        RAE API response
    """
    rae_client = RAEClient(tenant_id=tenant_id)

    payload = {
        "content": req.content,
        "source": req.source,
        "layer": req.layer,
        "tags": req.tags,
        "project": req.project,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rae_client.base_v1_url}/memory/store",
            json=payload,
            headers=rae_client.headers,
        )
        response.raise_for_status()
        return response.json()


@app.post("/memory/query")
async def query_memory_proxy(req: QueryMemoryRequest, tenant_id: str):
    """
    Proxy endpoint to query memory from the RAE API.

    Args:
        req: Memory query request
        tenant_id: Tenant ID for RAE API

    Returns:
        RAE API query results
    """
    rae_client = RAEClient(tenant_id=tenant_id)
    return rae_client.query_memory(req.query_text, req.k)


@app.delete("/memory/delete")
async def delete_memory_proxy(req: DeleteMemoryRequest, tenant_id: str):
    """
    Proxy endpoint to delete memory from the RAE API.

    Args:
        req: Memory deletion request
        tenant_id: Tenant ID for RAE API

    Returns:
        RAE API deletion response
    """
    rae_client = RAEClient(tenant_id=tenant_id)
    return rae_client.delete_memory(req.memory_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
