import asyncio, os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from redis import Redis
import redis.asyncio as aioredis
from rq import Queue
from rq.job import Job

from tasks import process_sap_report, on_success, on_failure
from events import CHANNEL, publish

load_dotenv(override=False)
REDIS_URL = os.environ["REDIS_URL"]
redis_conn = Redis.from_url(REDIS_URL)
q = Queue(connection=redis_conn)


class ConnectionManager:
    def __init__(self):
        self.active: set = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: str):
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)

manager = ConnectionManager()


async def redis_listener():
    """Runs for the life of the app: Redis pub/sub -> all connected browsers."""
    while True:
        try:
            r = aioredis.from_url(REDIS_URL)
            pubsub = r.pubsub()
            await pubsub.subscribe(CHANNEL)
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    data = msg["data"]
                    await manager.broadcast(data.decode() if isinstance(data, bytes) else data)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Listener error: {e} — reconnecting in 2s")
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(redis_listener())
    yield
    task.cancel()


app = FastAPI(title="SAP Job Queue System", lifespan=lifespan)


class ReportRequest(BaseModel):
    report_name: str
    pages: int


@app.get("/")
def root():
    redis_conn.ping()
    return {"message": "SAP Job Queue is running", "redis": "connected"}


@app.post("/submit")
def submit_job(request: ReportRequest):
    job = q.enqueue(process_sap_report, request.report_name, request.pages,
                    on_success=on_success, on_failure=on_failure)
    publish(redis_conn, job.id, "queued", request.report_name, request.pages)
    return {"job_id": job.id, "status": job.get_status().value}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = Job.fetch(job_id, connection=redis_conn)
    return {"job_id": job_id, "status": job.get_status().value, "result": job.result,
            "enqueued_at": str(job.enqueued_at), "ended_at": str(job.ended_at)}


@app.get("/queue")
def queue_status():
    return {"queued_jobs": len(q), "job_ids": q.job_ids}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()      # we only push; this just detects disconnects
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/ui")
def ui():
    return FileResponse("static/index.html", headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory="static"), name="static")