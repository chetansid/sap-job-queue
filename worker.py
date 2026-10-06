from rq import Queue, SimpleWorker
from redis import Redis
import os
from dotenv import load_dotenv
load_dotenv(override=False)
redis_conn = Redis.from_url(os.environ["REDIS_URL"])

q = Queue(connection=redis_conn)

if __name__ == "__main__":
    worker = SimpleWorker([q], connection=redis_conn)
    print("Worker started. Waiting for jobs...")
    worker.work()