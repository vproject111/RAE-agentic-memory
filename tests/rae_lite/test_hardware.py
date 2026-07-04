import pytest
from unittest.mock import MagicMock, patch, mock_open
from rae_lite.hardware import HardwareDetector

class TestHardwareDetector:
    
    @pytest.fixture
    def detector(self):
        return HardwareDetector()

    def test_profile_suggestion_gpu(self, detector):
        """Should suggest Profile D if good GPU is present."""
        gpu_info = {"has_nvidia": True, "vram_gb": 12.0}
        profile = detector.get_profile_suggestion(ram_gb=16.0, gpu_info=gpu_info)
        assert profile == "D"

    def test_profile_suggestion_high_ram(self, detector):
        """Should suggest Profile C if no GPU but high RAM."""
        gpu_info = {"has_nvidia": False, "vram_gb": 0.0}
        profile = detector.get_profile_suggestion(ram_gb=32.0, gpu_info=gpu_info)
        assert profile == "C"

    def test_profile_suggestion_mid_ram(self, detector):
        """Should suggest Profile B for 8-16GB RAM."""
        gpu_info = {"has_nvidia": False, "vram_gb": 0.0}
        profile = detector.get_profile_suggestion(ram_gb=12.0, gpu_info=gpu_info)
        assert profile == "B"

    def test_profile_suggestion_low_ram(self, detector):
        """Should suggest Profile A for low RAM."""
        gpu_info = {"has_nvidia": False, "vram_gb": 0.0}
        profile = detector.get_profile_suggestion(ram_gb=4.0, gpu_info=gpu_info)
        assert profile == "A"

    def test_linux_ram_detection(self, detector):
        """Test RAM detection on Linux using /proc/meminfo mock."""
        detector.is_windows = False
        
        mock_meminfo = "MemTotal:       16384000 kB\nMemFree:         8000000 kB"
        
        with patch("builtins.open", mock_open(read_data=mock_meminfo)):
            ram = detector.detect_ram()
            # 16384000 kB / 1024 / 1024 = 15.625 GB
            assert 15.0 < ram < 16.0

    def test_linux_cpu_detection(self, detector):
        """Test CPU detection on Linux using /proc/cpuinfo mock."""
        detector.is_windows = False
        
        mock_cpuinfo = "processor : 0\nvendor_id : GenuineIntel\nmodel name : Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz\n"
        
        with patch("builtins.open", mock_open(read_data=mock_cpuinfo)):
            info = detector.detect_cpu()
            assert "Intel" in info["name"]
            # Cores rely on os.cpu_count() which works natively

