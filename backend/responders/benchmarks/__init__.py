"""Responder budget-calibration benchmark package.

Vendors the frozen `budget-v1` prompt dataset, the frozen snapshot of the active
responder set, and the runner that executes them. Truncation is opt-in there so
hitting an output ceiling is measured, never raised, giving each model's natural
completion-token distribution for setting output budgets.
"""
from responders.benchmarks.prompts import (
    BENCHMARK_PROMPTS,
    BENCHMARK_VERSION,
    BenchmarkPrompt,
)
from responders.benchmarks.runner import (
    BenchmarkResult,
    BenchmarkSummary,
    ModelSummary,
    format_report,
    run_benchmark,
    summarize,
)
from responders.benchmarks.specs import BENCHMARK_RESPONDERS

__all__ = [
    "BENCHMARK_PROMPTS",
    "BENCHMARK_RESPONDERS",
    "BENCHMARK_VERSION",
    "BenchmarkPrompt",
    "BenchmarkResult",
    "BenchmarkSummary",
    "ModelSummary",
    "format_report",
    "run_benchmark",
    "summarize",
]