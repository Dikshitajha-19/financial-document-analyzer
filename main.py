from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import uuid
import datetime

from crewai import Crew, Process
from agents import financial_analyst
from task import analysis_task
from database import init_db, get_db, AnalysisRecord

# Initialize database tables on startup
init_db()

app = FastAPI(
    title="Financial Document Analyzer",
    description=(
        "AI-powered financial document analysis using CrewAI agents.\n\n"
        "Supports both **synchronous** analysis and **async queue-based** processing "
        "for handling multiple concurrent requests."
    ),
    version="2.0.0"
)


def run_crew_sync(query: str, file_path: str) -> str:
    """Run the CrewAI crew synchronously."""
    financial_crew = Crew(
        agents=[financial_analyst],
        tasks=[analysis_task],
        process=Process.sequential,
    )
    result = financial_crew.kickoff(inputs={
        "query": query,
        "file_path": file_path,
    })
    return str(result)


# ─────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "message": "Financial Document Analyzer API is running",
        "version": "2.0.0",
        "endpoints": {
            "sync_analyze": "POST /analyze",
            "async_analyze": "POST /analyze/async",
            "check_status": "GET /status/{task_id}",
            "history": "GET /history",
            "get_analysis": "GET /history/{task_id}",
        }
    }


# ─────────────────────────────────────────
# Synchronous Endpoint (simple, blocking)
# ─────────────────────────────────────────

@app.post("/analyze", tags=["Analysis"])
async def analyze_document(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
    db: Session = Depends(get_db)
):
    """
    **Synchronous** analysis — waits for the result before responding.
    Best for single requests. Use `/analyze/async` for concurrent requests.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    task_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{task_id}.pdf"

    try:
        os.makedirs("data", exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        if not query or query.strip() == "":
            query = "Analyze this financial document for investment insights"

        query = query.strip()
        start_time = datetime.datetime.utcnow()

        # Save record to DB
        record = AnalysisRecord(
            id=task_id,
            filename=file.filename,
            query=query,
            status="processing",
        )
        db.add(record)
        db.commit()

        # Run analysis
        result = run_crew_sync(query=query, file_path=file_path)

        # Update DB with result
        completed_at = datetime.datetime.utcnow()
        duration = (completed_at - start_time).total_seconds()

        record.status = "completed"
        record.result = result
        record.completed_at = completed_at
        record.duration_seconds = round(duration, 2)
        db.commit()

        return {
            "status": "success",
            "task_id": task_id,
            "query": query,
            "analysis": result,
            "file_processed": file.filename,
            "duration_seconds": round(duration, 2),
        }

    except Exception as e:
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == task_id).first()
        if record:
            record.status = "failed"
            record.error = str(e)
            record.completed_at = datetime.datetime.utcnow()
            db.commit()

        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


# ─────────────────────────────────────────
# Async Queue Endpoint (non-blocking)
# ─────────────────────────────────────────

@app.post("/analyze/async", tags=["Analysis"])
async def analyze_document_async(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
    db: Session = Depends(get_db)
):
    """
    **Asynchronous** analysis — immediately returns a `task_id`.
    Poll `GET /status/{task_id}` to check when the result is ready.
    Requires Redis and a running Celery worker.
    """
    try:
        from worker import analyze_document_task
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Queue worker unavailable. Ensure Redis is running and Celery is installed."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    task_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{task_id}.pdf"

    os.makedirs("data", exist_ok=True)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    if not query or query.strip() == "":
        query = "Analyze this financial document for investment insights"

    query = query.strip()

    # Save to DB as queued
    record = AnalysisRecord(
        id=task_id,
        filename=file.filename,
        query=query,
        status="queued",
    )
    db.add(record)
    db.commit()

    # Submit to Celery queue
    analyze_document_task.apply_async(
        args=[task_id, query, file_path],
        task_id=task_id
    )

    return {
        "status": "queued",
        "task_id": task_id,
        "message": "Document queued for analysis. Poll /status/{task_id} for results.",
        "status_url": f"/status/{task_id}",
    }


# ─────────────────────────────────────────
# Status Check Endpoint
# ─────────────────────────────────────────

@app.get("/status/{task_id}", tags=["Analysis"])
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Check the status of an async analysis task."""
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == task_id).first()

    if not record:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    response = {
        "task_id": task_id,
        "status": record.status,
        "filename": record.filename,
        "query": record.query,
        "created_at": record.created_at.isoformat(),
    }

    if record.status == "completed":
        response["analysis"] = record.result
        response["completed_at"] = record.completed_at.isoformat()
        response["duration_seconds"] = record.duration_seconds

    elif record.status == "failed":
        response["error"] = record.error
        response["completed_at"] = record.completed_at.isoformat() if record.completed_at else None

    return response


# ─────────────────────────────────────────
# History Endpoints
# ─────────────────────────────────────────

@app.get("/history", tags=["History"])
async def get_analysis_history(
    limit: int = 20,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve past analysis records.

    - **limit**: Number of records to return (default: 20, max: 100)
    - **status**: Filter by `queued`, `processing`, `completed`, or `failed`
    """
    limit = min(limit, 100)
    query_obj = db.query(AnalysisRecord).order_by(AnalysisRecord.created_at.desc())

    if status:
        query_obj = query_obj.filter(AnalysisRecord.status == status)

    records = query_obj.limit(limit).all()

    return {
        "total": len(records),
        "records": [
            {
                "task_id": r.id,
                "filename": r.filename,
                "query": r.query,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "duration_seconds": r.duration_seconds,
            }
            for r in records
        ]
    }


@app.get("/history/{task_id}", tags=["History"])
async def get_analysis_by_id(task_id: str, db: Session = Depends(get_db)):
    """Retrieve the full analysis result for a specific task."""
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == task_id).first()

    if not record:
        raise HTTPException(status_code=404, detail=f"Analysis '{task_id}' not found.")

    return {
        "task_id": record.id,
        "filename": record.filename,
        "query": record.query,
        "status": record.status,
        "analysis": record.result,
        "error": record.error,
        "created_at": record.created_at.isoformat(),
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        "duration_seconds": record.duration_seconds,
    }


@app.delete("/history/{task_id}", tags=["History"])
async def delete_analysis(task_id: str, db: Session = Depends(get_db)):
    """Delete a specific analysis record."""
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == task_id).first()

    if not record:
        raise HTTPException(status_code=404, detail=f"Analysis '{task_id}' not found.")

    db.delete(record)
    db.commit()

    return {"message": f"Analysis '{task_id}' deleted successfully."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
