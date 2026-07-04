"""Intelligence layer for orchestrator.

Phase 3 features:
- Performance tracking and analytics
- Historical data storage via RAE memory
- Adaptive routing based on past performance
- Model performance learning
"""

from .adaptive_router import AdaptiveModelRouter, LearningConfig, RoutingStrategy
from .analytics import ModelPerformance, PerformanceAnalytics, TaskPatternAnalysis
from .dashboard import PerformanceDashboard, intelligence_cli
from .performance_tracker import ExecutionRecord, PerformanceTracker, TaskOutcome
from .rae_integration import RAEMemoryIntegration, create_rae_integration

__all__ = [
    # Performance tracking
    "PerformanceTracker",
    "ExecutionRecord",
    "TaskOutcome",
    # Analytics
    "PerformanceAnalytics",
    "ModelPerformance",
    "TaskPatternAnalysis",
    # Adaptive routing
    "AdaptiveModelRouter",
    "LearningConfig",
    "RoutingStrategy",
    # RAE integration
    "RAEMemoryIntegration",
    "create_rae_integration",
    # Dashboard
    "PerformanceDashboard",
    "intelligence_cli",
]
