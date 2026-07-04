from __future__ import annotations

from app.celery_app import celery


QUEUE_MAP = {
    "python_io": "queue_python_io",
    "python_oop": "queue_python_oop",
    "python_numpy": "queue_python_numpy",
    "sql_query": "queue_sql",
    "cpp_io": "queue_cpp",
    "js_io": "queue_js",
}

TASK_NAME_MAP = {
    "python_io": "judger.tasks.run_python_io",
    "python_oop": "judger.tasks.run_pytest",
    "python_numpy": "judger.tasks.run_python_numpy",
    "sql_query": "judger.tasks.run_sql",
    "cpp_io": "judger.tasks.run_cpp",
    "js_io": "judger.tasks.run_js",
}


def enqueue_submission(execution_payload: dict):
    task_type = execution_payload.get("task_type", "python_io")
    queue = QUEUE_MAP.get(task_type, "queue_python_io")
    task_name = TASK_NAME_MAP.get(task_type, "judger.tasks.run_python_io")
    celery.send_task(task_name, args=[execution_payload], queue=queue)
