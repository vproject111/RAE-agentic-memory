"""
RAE-Lite Local HTTP Server (Enhanced).

FastAPI server running locally for RAE-Lite.
Serves static UI and provides API for ingestion and search.
"""

import os
import shutil
import yaml # Requires pyyaml
from pathlib import Path
from typing import List, Optional

import structlog
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rae_lite.service import RAELiteService

logger = structlog.get_logger(__name__)

# Config Loader
CONFIG_FILE = Path("config.yaml")
config = {
    "storage": {"data_dir": "rae_lite_storage"},
    "observer": {"enabled": False} 
}

if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, "r") as f:
            loaded_config = yaml.safe_load(f)
            if loaded_config:
                # Deep merge simplifiction
                if "storage" in loaded_config: config["storage"].update(loaded_config["storage"])
                if "observer" in loaded_config: config["observer"].update(loaded_config["observer"])
        logger.info(f"Loaded config from {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")

STORAGE_PATH = config["storage"]["data_dir"]
UPLOAD_DIR = "uploaded_files"

# Initialize Service with Configured Policy
service = RAELiteService(
    storage_path=STORAGE_PATH,
    watch_dir=UPLOAD_DIR,
    enable_observer=config["observer"]["enabled"] # Policy Driven
)

# Ensure dirs exist
Path(UPLOAD_DIR).mkdir(exist_ok=True)
Path(STORAGE_PATH).mkdir(exist_ok=True)

# FastAPI app
app = FastAPI(
    title="RAE-Lite",
    description="Universal Node for Windows",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class SearchRequest(BaseModel):
    query: str
    tenant_id: str = "local-user"

# API Endpoints

@app.on_event("startup")
async def startup_event():
    await service.start()

@app.on_event("shutdown")
async def shutdown_event():
    await service.stop()

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload files for ingestion."""
    uploaded_files = []
    for file in files:
        file_path = Path(UPLOAD_DIR) / file.filename
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_files.append(file.filename)
            # Ingestion is handled by Watcher automatically!
        except Exception as e:
            logger.error("upload_failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}")
    
    return {"status": "success", "files": uploaded_files, "message": "Ingestion started automatically."}

@app.post("/api/search")
async def search(request: SearchRequest):
    """Smart Search with Math Layer."""
    try:
        results = await service.query(request.query, request.tenant_id)
        return {"results": results}
    except Exception as e:
        logger.error("search_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def stats():
    """Get system stats."""
    return {
        "storage_path": STORAGE_PATH,
        "watched_dir": UPLOAD_DIR,
        "files_ingested": len(list(Path(UPLOAD_DIR).rglob("*"))),
        "db_size": os.path.getsize(Path(STORAGE_PATH) / "memories.db") if (Path(STORAGE_PATH) / "memories.db").exists() else 0
    }

# Serve Static Files (Frontend)
# We will create a simple index.html in rae_lite/ui/static
static_dir = Path(__file__).parent / "ui" / "static"
static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
