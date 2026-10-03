from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from rq import Queue
from rq.job import Job
from redis import Redis
from tasks import process_sap_report
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SAP Job Queue System")
redis_conn = Redis.from_url(os.getenv("REDIS_URL"))
q = Queue(connection=redis_conn)

class ReportRequest(BaseModel):
    report_name: str
    pages: int

@app.get("/")
def root():
    redis_conn.ping()
    return {"message": "SAP Job Queue is running", "redis": "connected"}

@app.post("/submit")
def submit_job(request: ReportRequest):
    job = q.enqueue(process_sap_report, request.report_name, request.pages)
    return {
        "job_id": job.id,
        "status": job.get_status().value,
        "message": f"Job submitted. Check status at /status/{job.id}"
    }

@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = Job.fetch(job_id, connection=redis_conn)
    return {
        "job_id": job_id,
        "status": job.get_status().value,
        "result": job.result,
        "enqueued_at": str(job.enqueued_at),
        "ended_at": str(job.ended_at)
    }

@app.get("/queue")
def queue_status():
    return {
        "queued_jobs": len(q),
        "job_ids": q.job_ids
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/ui")
def ui():
    return FileResponse("static/index.html")