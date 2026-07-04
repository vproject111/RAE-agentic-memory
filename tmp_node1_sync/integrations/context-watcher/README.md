# RAE Context Watcher

HTTP daemon that watches project files and automatically feeds them into the RAE Memory Engine.

**Note**: This is NOT the Model Context Protocol (MCP) server. For MCP integration with IDEs (Claude Desktop, Cursor, Cline), see [../mcp/](../mcp/).

## What is Context Watcher?

Context Watcher is a lightweight HTTP service that:
- Monitors file system changes in your projects
- Automatically stores updated files in RAE memory
- Provides HTTP API for project management
- Runs as a local daemon on port 8001

## Features

- **File System Watching**: Real-time monitoring of project directories
- **Automatic Memory Storage**: Changed files are automatically sent to RAE
- **Multi-Project Support**: Watch multiple projects with separate tenant isolation
- **Configurable Patterns**: Filter files by extension (py, js, ts, md, etc.)
- **HTTP API**: REST API for managing watched projects
- **Prometheus Metrics**: Built-in observability
- **Structured Logging**: JSON-formatted logs for easy parsing

## Installation

### From Source

```bash
cd integrations/context-watcher
pip install -e .
```

### With Development Dependencies

```bash
pip install -e ".[dev]"
```

### Verify Installation

```bash
context-watcher --help
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
RAE_API_URL=http://localhost:8000
RAE_API_KEY=your-api-key-here
```

## Usage

### Start the Daemon

```bash
context-watcher
```

The server will start on `http://0.0.0.0:8001`.

### Register a Project

Register a directory to watch:

```bash
curl -X POST http://localhost:8001/projects \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/your/project",
    "tenant_id": "my-tenant"
  }'
```

Response:

```json
{
  "project_id": "my-tenant-project-name",
  "message": "Started watching project 'my-tenant-project-name'."
}
```

### List Watched Projects

```bash
curl http://localhost:8001/projects
```

Response:

```json
{
  "my-tenant-project-name": {
    "path": "/path/to/your/project",
    "tenant_id": "my-tenant"
  }
}
```

### Check Status

```bash
curl http://localhost:8001/status
```

Response:

```json
{
  "status": "running",
  "watched_projects_count": 1
}
```

### Unregister a Project

```bash
curl -X DELETE http://localhost:8001/projects/my-tenant-project-name
```

## Architecture

### Component Diagram

```
┌─────────────────────────────────────┐
│    File System                      │
│    (/path/to/project)               │
└─────────────┬───────────────────────┘
              │ file events
              │
┌─────────────▼───────────────────────┐
│    Watchdog Observer                │
│    (watches *.py, *.js, *.md, etc.) │
└─────────────┬───────────────────────┘
              │ callback
              │
┌─────────────▼───────────────────────┐
│    Context Watcher (FastAPI)        │
│    - Project management API         │
│    - File change callbacks          │
│    - RAE client integration         │
└─────────────┬───────────────────────┘
              │ HTTP POST /v1/memory/store
              │
┌─────────────▼───────────────────────┐
│    RAE Memory API                   │
│    (port 8000)                      │
└─────────────────────────────────────┘
```

### Watched File Patterns

By default, the watcher monitors:

- `*.py` - Python files
- `*.js` - JavaScript files
- `*.ts` - TypeScript files
- `*.md` - Markdown files
- `*.txt` - Text files
- `*.json` - JSON files
- `*.yaml`, `*.yml` - YAML files

Ignored patterns:

- `.git/*` - Git internals
- `__pycache__/*` - Python cache
- `.idea/*`, `.vscode/*` - IDE folders
- `*.log` - Log files

### Memory Storage

When a file changes:

1. **File Read**: Content is read from disk
2. **Payload Creation**: File path, content, and metadata are packaged
3. **RAE API Call**: `POST /v1/memory/store` with:
   - `content`: File contents
   - `source`: File path
   - `layer`: `ltm` (long-term memory)
   - `tags`: File extension + `file-watcher`

## HTTP API Reference

### `GET /status`

Returns daemon status.

**Response**:

```json
{
  "status": "running",
  "watched_projects_count": 2
}
```

### `POST /projects`

Register a new project to watch.

**Request Body**:

```json
{
  "path": "/absolute/path/to/project",
  "tenant_id": "tenant-identifier"
}
```

**Response**:

```json
{
  "project_id": "tenant-project-name",
  "message": "Started watching project 'tenant-project-name'."
}
```

### `GET /projects`

List all watched projects.

**Response**:

```json
{
  "project-1": {
    "path": "/path/to/project1",
    "tenant_id": "tenant-1"
  },
  "project-2": {
    "path": "/path/to/project2",
    "tenant_id": "tenant-2"
  }
}
```

### `DELETE /projects/{project_id}`

Stop watching a project.

**Response**:

```json
{
  "message": "Stopped watching project 'project-id'."
}
```

### `POST /memory/store`

Proxy endpoint for storing memories directly (bypasses file watching).

**Query Parameter**: `tenant_id`

**Request Body**:

```json
{
  "content": "Memory content",
  "source": "source-identifier",
  "layer": "ltm",
  "tags": ["tag1", "tag2"],
  "project": "project-name"
}
```

### `POST /memory/query`

Proxy endpoint for querying memories.

**Query Parameter**: `tenant_id`

**Request Body**:

```json
{
  "query_text": "search query",
  "k": 10
}
```

### `DELETE /memory/delete`

Proxy endpoint for deleting memories.

**Query Parameter**: `tenant_id`

**Request Body**:

```json
{
  "memory_id": "memory-uuid"
}
```

## Monitoring & Observability

### Prometheus Metrics

The daemon exposes metrics on `/metrics`:

- `files_synced_total` - Total files synced to RAE
- `watched_projects_total` - Number of active watched projects
- `file_sync_errors_total` - File sync errors
- `file_sync_duration_seconds` - Time to sync a file

### Structured Logging

Logs are output in structured format:

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "info",
  "message": "File change detected",
  "tenant_id": "my-tenant",
  "file_path": "/path/to/file.py"
}
```

## Development

### Running Tests

```bash
pytest
```

### With Coverage

```bash
pytest --cov=context_watcher --cov-report=html
```

### Type Checking

```bash
mypy src/context_watcher
```

### Linting and Formatting

```bash
black src/context_watcher
ruff check src/context_watcher
```

## Troubleshooting

### Daemon Won't Start

1. Check port 8001 is not in use: `lsof -i :8001`
2. Verify environment variables are set
3. Ensure Python 3.10+ is installed

### Files Not Being Watched

1. Check project is registered: `curl http://localhost:8001/projects`
2. Verify file extension is in watched patterns (see `watcher.py`)
3. Check daemon logs for errors
4. Ensure directory exists and is readable

### RAE API Connection Errors

1. Verify RAE API is running: `curl http://localhost:8000/health`
2. Check `RAE_API_URL` environment variable
3. Ensure API key is valid
4. Check network connectivity

### High Memory Usage

If watching large projects:

1. Add more ignore patterns in `watcher.py`
2. Exclude `node_modules`, `dist`, `build` directories
3. Reduce watched file patterns

## Performance

Benchmarks on typical project (1000 files):

- **Startup Time**: < 1 second
- **File Change Detection**: 10-50ms
- **Memory Storage**: 100-200ms per file
- **Memory Footprint**: ~50-100MB (base) + ~10KB per watched file

## Security

- ✅ Tenant isolation via `X-Tenant-Id` header
- ✅ File path validation to prevent directory traversal
- ✅ No execution of file contents
- ✅ HTTP-only (use reverse proxy for HTTPS)
- ✅ Local daemon (not exposed to internet by default)

## Use Cases

1. **Continuous Context Capture**: Automatically feed all code changes to RAE
2. **Team Knowledge Base**: Share project context across team members
3. **CI/CD Integration**: Watch build outputs and store artifacts
4. **Documentation Generation**: Auto-capture README and doc changes
5. **Code Review Context**: Provide historical context for file changes

## Comparison with MCP Server

| Feature | Context Watcher | MCP Server |
|---------|----------------|------------|
| Protocol | HTTP REST | STDIO JSON-RPC |
| Use Case | File watching | IDE integration |
| Client | Any HTTP client | Claude Desktop, Cursor, Cline |
| Runs As | Daemon (background) | On-demand (per IDE session) |
| Port | 8001 | N/A (STDIO) |

## Contributing

See main repository [CONTRIBUTING.md](../../CONTRIBUTING.md).

## License

Apache License 2.0 - see [LICENSE](../../LICENSE) file

## Support

- **GitHub Issues**: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
- **Documentation**: See [docs/integrations/context_watcher_daemon.md](../../docs/integrations/context_watcher_daemon.md)
- **Community**: Discussions tab on GitHub

## Related

- [MCP Server](../mcp/README.md) - IDE integration via Model Context Protocol
- [RAE Memory API](../../apps/memory_api/README.md) - Core RAE API documentation
