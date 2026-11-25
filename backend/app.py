"""Service starter. Real inference jobs/exports remain a team deliverable."""
from fastapi import FastAPI

app = FastAPI(title="Earthquake inspection API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "inference_ready": False}
