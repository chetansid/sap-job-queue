import json, time

CHANNEL = "job-events"

def publish(connection, job_id, status, name=None, pages=None, result=None, error=None):
    connection.publish(CHANNEL, json.dumps({
        "job_id": job_id, "status": status, "name": name,
        "pages": pages, "result": result, "error": error, "ts": time.time(),
    }))