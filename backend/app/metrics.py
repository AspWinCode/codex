from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge

SUBMISSIONS_TOTAL = Counter(
    "submissions_total",
    "Total submissions received",
    ["task_type"],
)

SUBMISSIONS_VERDICT = Counter(
    "submissions_verdict_total",
    "Submission verdicts",
    ["verdict"],
)

SUBMISSION_LATENCY = Histogram(
    "submission_processing_seconds",
    "Time from submission creation to result",
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60, 120],
)

ACTIVE_USERS = Gauge(
    "active_users",
    "Approximate active users (recent API calls)",
)

QUEUE_SIZE = Gauge(
    "judger_queue_size",
    "Number of submissions in queue",
    ["queue"],
)
