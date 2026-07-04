import asyncio
import logging
import os
import platform
import socket
import sys
from typing import Any, Dict, List, Optional

import httpx
import yaml

# Constants
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
DEFAULT_API_URL = "http://localhost:8000"

# Logging setup
# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "agent.log")),
    ],
)
logger = logging.getLogger("node_agent")


class NodeAgent:
    def __init__(self):
        self.config = self._load_config()
        self.node_id = self.config.get("node_id", socket.gethostname())
        self.api_key = self.config.get("api_key", "dev-secret")
        self.base_url = self.config.get("rae_endpoint", DEFAULT_API_URL).rstrip("/")
        self.heartbeat_interval = self.config.get("heartbeat_interval_sec", 30)
        self.capabilities = self.config.get("capabilities", {})

        # Override capabilities with auto-detection if enabled
        if self.config.get("auto_detect_capabilities", True):
            self._detect_capabilities()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        return {}

    def _detect_capabilities(self):
        """Detect system hardware and software."""
        self.capabilities["os"] = platform.system()
        self.capabilities["hostname"] = socket.gethostname()
        self.capabilities["cpu_count"] = os.cpu_count()
        self.capabilities["arch"] = platform.machine()

        # GPU Detection (NVIDIA)
        try:
            import subprocess

            smi_out = subprocess.check_output(["nvidia-smi", "-L"], text=True)
            self.capabilities["gpu"] = True
            self.capabilities["gpu_info"] = smi_out.strip()
            self.capabilities["vram_gb"] = 16  # Placeholder/Estimate or parse smi_out
        except Exception:
            self.capabilities["gpu"] = False

    async def register(self, client: httpx.AsyncClient):
        payload = {
            "node_id": self.node_id,
            "api_key": self.api_key,
            "capabilities": self.capabilities,
        }
        try:
            url = f"{self.base_url}/control/nodes/register"
            logger.info(f"Registering at {url}...")
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info(f"Registered successfully as {self.node_id}")
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            # Don't raise, just retry later or run in degraded mode
            # Actually, without registration, we shouldn't proceed?
            # We'll retry in the loop.
            pass

    async def heartbeat_loop(self, client: httpx.AsyncClient):
        while True:
            try:
                payload = {"node_id": self.node_id, "status": "ONLINE"}
                await client.post(
                    f"{self.base_url}/control/nodes/heartbeat", json=payload
                )
                logger.debug("Heartbeat sent")
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")

            await asyncio.sleep(self.heartbeat_interval)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type")
        payload = task.get("payload", {})
        logger.info(f"Processing task {task.get('id')} of type {task_type}")

        if task_type == "llm_inference":
            return await self._execute_ollama(payload)
        elif task_type in ["code_verify_cycle", "quality_loop"]:
            return await self._execute_code_cycle(payload)
        elif task_type == "shell_command":
            return await self._execute_shell_command(payload)

        return {"status": "success", "output": "unknown_task_type"}

    async def _execute_shell_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a shell command and return output."""
        command = payload.get("command")
        cwd = payload.get("cwd", os.getcwd())
        env = {**os.environ, **payload.get("env", {})}

        if not command:
            return {"status": "error", "error": "No command provided"}

        logger.info(f"Executing shell command: {command} in {cwd}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )
            stdout, stderr = await process.communicate()

            return {
                "status": "success" if process.returncode == 0 else "error",
                "returncode": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _call_ollama(
        self, model: str, prompt: str, system: str = ""
    ) -> Dict[str, Any]:
        ollama_url = self.config.get("ollama_api_url", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "system": system,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                return {"status": "success", "response": resp.json().get("response")}
            except Exception as e:
                return {"status": "error", "error": str(e)}

    async def _fetch_from_rae(self, memory_id: str) -> Optional[str]:
        """Fetch a specific memory content from the Control Node."""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-API-Key": self.api_key}
                resp = await client.get(
                    f"{self.base_url}/v1/memory/{memory_id}", headers=headers
                )
                if resp.status_code == 200:
                    return resp.json().get("content")
        except Exception as e:
            logger.error(f"Failed to fetch from RAE: {e}")
        return None

    async def _search_rae(self, query: str) -> List[Dict[str, Any]]:
        """Search RAE for relevant context."""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-API-Key": self.api_key}
                payload = {"query": query, "k": 5}
                resp = await client.post(
                    f"{self.base_url}/v1/memory/query", json=payload, headers=headers
                )
                if resp.status_code == 200:
                    return resp.json().get("results", [])
        except Exception as e:
            logger.error(f"RAE Search failed: {e}")
        return []

    async def _execute_code_cycle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Writer/Reviewer cycle with RAE context awareness."""
        writer_model = payload.get("writer_model", "deepseek-coder:33b")
        reviewer_model = payload.get("reviewer_model", "deepseek-coder:6.7b")
        instruction = payload.get("prompt") or payload.get("task", "")

        # 0. FETCH CONTEXT FROM RAE
        rae_context = ""
        # Pull protocol automatically to ensure compliance
        protocol = await self._search_rae("AGENT_CORE_PROTOCOL agnosticism rules")
        if protocol:
            rae_context += "### RAE PROTOCOL RULES\n" + protocol[0]["content"] + "\n\n"

        # Pull specific code if memory_id provided
        mem_id = payload.get("memory_id")
        code_content = payload.get("diff") or payload.get("code") or ""
        if mem_id:
            fetched_code = await self._fetch_from_rae(mem_id)
            if fetched_code:
                code_content = fetched_code

        # 1. WRITE (Analysis/Drafting)
        writer_system = (
            "You are an expert Security and Performance Auditor with access to RAE Memory. "
            "Analyze the code provided in the prompt against the RAE Protocol rules. "
            "Be precise, technical, and focused on agnosticism."
        )
        write_prompt = (
            f"{rae_context}"
            f"INSTRUCTION: {instruction}\n\n"
            "CODE TO ANALYZE:\n"
            f"{code_content}\n\n"
            "Perform the analysis now."
        )

        logger.info(
            f"Phase 1: Writing code/analysis with {writer_model} (RAE context included)"
        )
        write_result = await self._call_ollama(
            writer_model, write_prompt, system=writer_system
        )
        if write_result["status"] == "error":
            return write_result
        initial_output = write_result["response"]

        # 2. REVIEW
        logger.info(f"Phase 2: Reviewing output with {reviewer_model}")
        reviewer_system = (
            "You are a Senior Python Architect at RAE Project. Your mission is to enforce the highest quality standards. "
            "You MUST check if the code/analysis: "
            "1. Includes OpenTelemetry instrumentation (@trace_agent_operation). "
            "2. Includes unit tests (mocking async dependencies). "
            "3. Follows Async-First principles. "
            "4. Has NO absolute paths."
        )
        review_prompt = (
            "Critically review the following code/analysis. "
            "If it meets ALL RAE standards, respond with 'PASSED' followed by a short summary. "
            "If anything is missing (especially Telemetry or Tests), respond with 'REJECTED' and list specific issues.\n\n"
            f"OUTPUT TO REVIEW:\n{initial_output}"
        )
        review_result = await self._call_ollama(
            reviewer_model, review_prompt, system=reviewer_system
        )

        return {
            "status": "success",
            "writer_output": initial_output,
            "review_report": review_result.get("response", "Review failed"),
            "is_passed": "PASSED" in review_result.get("response", ""),
        }

    async def _execute_ollama(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._call_ollama(
            payload.get("model", "deepseek-coder:33b"),
            payload.get("prompt", ""),
            payload.get("system", ""),
        )

    async def task_loop(self, client: httpx.AsyncClient):
        poll_url = f"{self.base_url}/control/tasks_poll"
        while True:
            try:
                resp = await client.get(poll_url, params={"node_id": self.node_id})
                if resp.status_code == 200:
                    task = resp.json()
                    if task:
                        result = {}
                        error = None
                        try:
                            result = await self.process_task(task)
                        except Exception as e:
                            logger.error(f"Task execution failed: {e}")
                            error = str(e)

                        # Submit result
                        submit_url = (
                            f"{self.base_url}/control/tasks/{task['id']}/result"
                        )
                        payload = {
                            "task_id": task["id"],
                            "result": result,
                            "error": error,
                        }
                        await client.post(submit_url, json=payload)
                        logger.info(f"Task {task['id']} result submitted")
            except Exception:
                # Reduce noise
                pass

            await asyncio.sleep(2)  # Normal poll interval

    async def run(self):
        async with httpx.AsyncClient(timeout=10.0) as client:
            await self.register(client)
            await asyncio.gather(self.heartbeat_loop(client), self.task_loop(client))


if __name__ == "__main__":
    agent = NodeAgent()
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Agent stopping...")
