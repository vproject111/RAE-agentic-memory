import subprocess
import time
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SSHTunnelManager:
    """
    Manages local or remote (reverse) SSH tunnels.
    Monitors liveness, retries with exponential backoff on port clashes, and restarts on termination.
    """

    def __init__(
        self,
        local_port: int,
        remote_port: int,
        ssh_host: str,
        ssh_user: str,
        ssh_key_path: Optional[str] = None,
        is_reverse: bool = True,
        max_retries: int = 5,
        base_backoff: float = 1.0,
    ):
        self.local_port = local_port
        self.remote_port = remote_port
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_key_path = ssh_key_path
        self.is_reverse = is_reverse
        self.max_retries = max_retries
        self.base_backoff = base_backoff

        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.lock = threading.Lock()
        self.monitor_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        with self.lock:
            if self.running:
                return
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("SSH Tunnel Monitor started.")

    def stop(self) -> None:
        with self.lock:
            self.running = False
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=3)
                except Exception as e:
                    logger.warning(f"Failed to terminate SSH process: {e}")
                self.process = None
            logger.info("SSH Tunnel Monitor stopped.")

    def _monitor_loop(self) -> None:
        retries = 0
        while self.running:
            try:
                # Check if process is running
                if self.process is None or self.process.poll() is not None:
                    if self.process is not None:
                        logger.warning(f"SSH process exited with code {self.process.poll()}. Restarting...")
                        self.process = None

                    # If we had a recent clash or failure, apply backoff
                    if retries > 0:
                        backoff = min(self.base_backoff * (2 ** (retries - 1)), 60.0)
                        logger.info(f"Retrying SSH tunnel in {backoff:.2f} seconds...")
                        
                        # Wait in small increments so we can exit quickly if stop() is called
                        slept = 0.0
                        step = min(0.05, backoff)
                        while slept < backoff and self.running:
                            time.sleep(step)
                            slept += step

                    if not self.running:
                        break

                    success = self._run_tunnel()
                    if success:
                        retries = 0  # reset on successful start
                    else:
                        retries += 1
                else:
                    # Tunnel is healthy, sleep and check again
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Error in SSH tunnel monitor loop: {e}")
                time.sleep(5)

    def _run_tunnel(self) -> bool:
        cmd = ["ssh", "-o", "ExitOnForwardFailure=yes", "-o", "ConnectTimeout=10", "-N"]

        if self.ssh_key_path:
            cmd.extend(["-i", self.ssh_key_path])

        if self.is_reverse:
            # -R remote_port:localhost:local_port
            cmd.extend(["-R", f"{self.remote_port}:localhost:{self.local_port}"])
        else:
            # -L local_port:localhost:remote_port
            cmd.extend(["-L", f"{self.local_port}:localhost:{self.remote_port}"])

        cmd.append(f"{self.ssh_user}@{self.ssh_host}")

        logger.info(f"Starting SSH tunnel command: {' '.join(cmd)}")
        try:
            # We capture stderr to detect port clashes
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Wait a short moment to see if it immediately exits due to ExitOnForwardFailure
            time.sleep(0.1)
            poll = self.process.poll()
            if poll is not None:
                _, stderr = self.process.communicate()
                logger.error(f"SSH tunnel failed to start. Exit code: {poll}, Error: {stderr.strip()}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to spawn SSH process: {e}")
            return False
