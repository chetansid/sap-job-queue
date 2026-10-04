from rq import Queue, Worker
from redis import Redis
import os
from dotenv import load_dotenv

load_dotenv(override=False)

redis_conn = Redis.from_url(os.getenv("REDIS_URL"))
q = Queue(connection=redis_conn)

if __name__ == "__main__":
    worker = Worker([q], connection=redis_conn)
    print("Worker started. Waiting for jobs...")
    worker.work()