from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock


@dataclass(frozen=True, slots=True)
class MetricsSnapshot:
    total_requests: int
    total_errors: int
    avg_latency_ms: float
    total_code_executions: int
    avg_code_execution_ms: float
    runner_status_counts: dict[str, int] = field(default_factory=dict)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._total_requests = 0
        self._total_errors = 0
        self._total_latency_ms = 0.0
        self._total_code_executions = 0
        self._total_code_execution_ms = 0.0
        self._runner_status_counts: dict[str, int] = {}

    def record_request(self, *, status_code: int, latency_ms: float) -> None:
        with self._lock:
            self._total_requests += 1
            self._total_latency_ms += latency_ms
            if status_code >= 400:
                self._total_errors += 1

    def record_code_execution(self, *, duration_ms: float, runner_status: str) -> None:
        with self._lock:
            self._total_code_executions += 1
            self._total_code_execution_ms += duration_ms
            self._runner_status_counts[runner_status] = (
                self._runner_status_counts.get(runner_status, 0) + 1
            )

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            avg_latency_ms = (
                self._total_latency_ms / self._total_requests
                if self._total_requests
                else 0.0
            )
            avg_code_execution_ms = (
                self._total_code_execution_ms / self._total_code_executions
                if self._total_code_executions
                else 0.0
            )
            return MetricsSnapshot(
                total_requests=self._total_requests,
                total_errors=self._total_errors,
                avg_latency_ms=round(avg_latency_ms, 3),
                total_code_executions=self._total_code_executions,
                avg_code_execution_ms=round(avg_code_execution_ms, 3),
                runner_status_counts=dict(self._runner_status_counts),
            )
