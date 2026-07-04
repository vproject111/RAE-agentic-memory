import subprocess

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
# This script is designed to run via SSH Stdio transport
mcp = FastMCP("Compute Node")


@mcp.tool()
def execute_shell(command: str) -> str:
    """
    Execute a shell command on the node.
    Use with caution. Timeout is set to 300 seconds.
    """
    try:
        # Run command with timeout
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=300
        )
        output = f"Exit Code: {result.returncode}\n"
        output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 300 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"


@mcp.tool()
def get_system_info() -> str:
    """Get system hardware information (OS, GPU, RAM)."""
    info = []

    # OS Info
    try:
        info.append(
            f"OS: {subprocess.check_output(['uname', '-a'], text=True).strip()}"
        )
    except Exception:
        pass

    # GPU Info
    try:
        gpu_info = subprocess.check_output(["nvidia-smi", "-L"], text=True).strip()
        info.append(f"GPU:\n{gpu_info}")
    except Exception:
        info.append("GPU: nvidia-smi failed or not available")

    # Memory Info (Linux)
    try:
        mem_info = subprocess.check_output(["free", "-h"], text=True).strip()
        info.append(f"Memory:\n{mem_info}")
    except Exception:
        pass

    return "\n\n".join(info)


if __name__ == "__main__":
    # Standard MCP behavior: communicate via stdio
    # This allows the server to be used over SSH tunnels automatically
    mcp.run()
