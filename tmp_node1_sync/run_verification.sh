#!/bin/bash
export RAE_API_URL="http://localhost:8000"
source .venv/bin/activate
python3 verify_mcp.py
