"""
Queue Worker using Celery + Redis.
Handles concurrent document analysis requests without blocking the API.

To run the worker:
    celery -A worker worker --loglevel=info --concurrency=4
"""

import os
import datetime
import time

from celery import Celery
from dotenv import load_dotenv
load_dotenv()

from crewai import Crew, Process
from agents import financial_analyst
from task import analysis_task
from database import SessionLocal, AnalysisRecord

# Redis is used as both the message broker and result backend.
# Make sure Redis is running: docker run -d -p 6379:6379 redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "financial_analyzer",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=86400,  # Results expire after 24 hours
)


@celery_app.task(bind=True, name="analyze_document")
def analyze_document_task(self, task_id: str, query: str, file_path: str):
    """
    Celery task that runs the CrewAI crew asynchronously.
    Updates the database with status, result, and timing info.
    """
    db = SessionLocal()
    start_time = time.time()

    try:
        # Mark as processing
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == task_id).first()
        if record:
            record.status = "processing"
            db.commit()

        # Run the CrewAI crew
        financial_crew = Crew(
            agents=[financial_analyst],
            tasks=[analysis_task],
            process=Process.sequential,
        )

        result = financial_crew.kickoff(inputs={
            "query": query,
            "file_path": file_path,
        })

        duration = time.time() - start_time

        # Save result to DB
        if record:
            record.status = "completed"
            record.result = str(result)
            record.completed_at = datetime.datetime.utcnow()
            record.duration_seconds = round(duration, 2)
            db.commit()

        return {"status": "completed", "result": str(result)}

    except Exception as e:
        duration = time.time() - start_time

        # Save error to DB
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == task_id).first()
        if record:
            record.status = "failed"
            record.error = str(e)
            record.completed_at = datetime.datetime.utcnow()
            record.duration_seconds = round(duration, 2)
            db.commit()

        raise self.retry(exc=e, countdown=5, max_retries=2)

    finally:
        # Clean up uploaded file after processing
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        db.close()
