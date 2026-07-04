# MCP (Memory Context Provider) Server

The MCP Server is a local daemon that automatically feeds context from your local development projects into the RAE Memory Engine. It's designed to be editor-agnostic, meaning it can work with any code editor.

## How it Works

1.  You start the MCP Server in the background.
2.  You register one or more project directories with the server.
3.  The server continuously monitors these directories for file changes (creations, modifications).
4.  When a change is detected, the server reads the file's content and sends it to the RAE Memory API's `/memory/store` endpoint.
5.  This ensures your RAE instance always has the latest context from your codebase.

## Setup

1.  **Configure RAE API**: Ensure your RAE Memory API is running and accessible.
2.  **Configure MCP Server**:
    Create a `.env` file in the `integrations/mcp-server/` directory:

    ```
    RAE_API_URL="http://localhost:8000"
    RAE_API_KEY="your-secret-rae-api-key"
    ```

## Usage

1.  Navigate to the MCP Server directory:
    ```bash
    cd integrations/mcp-server
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the server (in the background or a separate terminal):
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8001
    ```
4.  Register a project to watch. Replace `/path/to/your/project` with the actual path to your project and `my-project-tenant` with your desired tenant ID.

    ```bash
    curl -X POST "http://localhost:8001/projects" \
    -H "Content-Type: application/json" \
    -d '{"path": "/path/to/your/project", "tenant_id": "my-project-tenant"}'
    ```
    The `tenant_id` specified here will be used when storing memories in RAE.

5.  List watched projects:
    ```bash
    curl http://localhost:8001/projects
    ```

6.  Unregister a project:
    ```bash
    curl -X DELETE "http://localhost:8001/projects/my-project-tenant-your-project-name"
    ```
    The `project_id` is typically a combination of `tenant_id` and the base name of the project path.

