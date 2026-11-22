import time
from rq import get_current_job
from events import publish

def process_sap_report(report_name: str, pages: int) -> dict:
    job = get_current_job()
    publish(job.connection, job.id, "started", report_name, pages)
    time.sleep(pages * 0.5)
    if "fail" in report_name.lower():          # lets you trigger a failed event on demand
        raise RuntimeError("Simulated failure")
    return {"report_name": report_name, "pages_processed": pages, "status": "completed"}

def on_success(job, connection, result, *args, **kwargs):
    publish(connection, job.id, "finished", job.args[0], job.args[1], result=result)

def on_failure(job, connection, type, value, traceback):
    publish(connection, job.id, "failed", job.args[0], job.args[1], error=str(value))