import subprocess
import platform
import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class HardwareDetector:
    """Wykrywa podzespoły sprzętowe na systemie Windows w celu dobrania profilu LLM."""

    def __init__(self):
        self.is_windows = platform.system() == "Windows"

    def detect_all(self) -> Dict[str, Any]:
        """Wykonuje pełną sondę sprzętową."""
        ram_gb = self.detect_ram()
        cpu_info = self.detect_cpu()
        gpu_info = self.detect_gpu()

        return {
            "ram_gb": ram_gb,
            "cpu": cpu_info,
            "gpu": gpu_info,
            "os": platform.platform(),
            "suggested_profile": self.get_profile_suggestion(ram_gb, gpu_info)
        }

    def detect_ram(self) -> float:
        """Wykrywa całkowitą pamięć RAM w GB."""
        try:
            if self.is_windows:
                output = subprocess.check_output(["wmic", "computersystem", "get", "TotalPhysicalMemory"], text=True)
                numbers = re.findall(r"\d+", output)
                if numbers:
                    bytes_val = int(numbers[0])
                    return round(bytes_val / (1024**3), 2)
            else:
                # Linux /proc/meminfo
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal" in line:
                            parts = line.split()
                            kb_val = int(parts[1])
                            return round(kb_val / (1024**2), 2)
        except Exception as e:
            logger.error(f"Błąd wykrywania RAM: {e}")
        return 0.0

    def detect_cpu(self) -> Dict[str, Any]:
        """Wykrywa nazwę i liczbę rdzeni procesora."""
        info = {"name": "Unknown", "cores": 0}
        try:
            info["cores"] = subprocess.os.cpu_count() or 0
            if self.is_windows:
                output = subprocess.check_output(["wmic", "cpu", "get", "name"], text=True)
                lines = [l.strip() for l in output.split("\n") if l.strip() and "Name" not in l]
                if lines:
                    info["name"] = lines[0]
            else:
                # Linux /proc/cpuinfo
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            info["name"] = line.split(":")[1].strip()
                            break
        except Exception as e:
            logger.error(f"Błąd wykrywania CPU: {e}")
        return info

    def detect_gpu(self) -> Dict[str, Any]:
        """Wykrywa obecność procesora graficznego NVIDIA i ilość VRAM."""
        info = {"has_nvidia": False, "name": "None", "vram_gb": 0.0}
        
        # Próba przez nvidia-smi
        try:
            output = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], text=True)
            parts = output.strip().split(",")
            if len(parts) >= 2:
                info["has_nvidia"] = True
                info["name"] = parts[0].strip()
                info["vram_gb"] = round(float(parts[1].strip()) / 1024, 2)
                return info
        except Exception:
            pass

        # Próba przez wmic (ogólne wykrywanie GPU)
        try:
            if self.is_windows:
                output = subprocess.check_output(["wmic", "path", "win32_VideoController", "get", "name"], text=True)
                if "NVIDIA" in output:
                    info["has_nvidia"] = True
                    lines = [l.strip() for l in output.split("\n") if l.strip() and "Name" not in l]
                    info["name"] = lines[0] if lines else "NVIDIA GPU"
        except Exception:
            pass

        return info

    def get_profile_suggestion(self, ram_gb: float, gpu_info: Dict[str, Any]) -> str:
        """Mapuje sprzęt na profil operacyjny (A, B, C lub D)."""
        # Priorytet dla GPU
        if gpu_info["has_nvidia"] and gpu_info["vram_gb"] >= 6.0:
            return "D"  # GPU Acceleration (7B+ GGUF)
        
        if ram_gb >= 16.0:
            return "C"  # 3-7B GGUF on CPU
        elif ram_gb >= 8.0:
            return "B"  # 1-2B GGUF on CPU
        else:
            return "A"  # No LLM (Math Only)

if __name__ == "__main__":
    detector = HardwareDetector()
    print(detector.detect_all())
