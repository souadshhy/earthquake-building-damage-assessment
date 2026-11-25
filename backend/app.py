"""FastAPI backend service with async job lifecycle and report exports."""
from __future__ import annotations

import asyncio
import copy
import csv
import io
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(title="Earthquake Inspection API", version="0.2.0")

ROOT_DIR = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT_DIR / "frontend" / "src" / "data" / "result.fixture.json"

PREPARED_PAIRS: List[Dict[str, str]] = [
    {
        "pair_id": "haiti-2010-port-au-prince-01",
        "label": "Haiti 2010 — Port-au-Prince Sector 01",
        "region": "Port-au-Prince, Haiti",
        "event_date": "2010-01-12",
    },
    {
        "pair_id": "turkiye-2023-kahramanmaras-02",
        "label": "Türkiye 2023 — Kahramanmaraş Sector 02",
        "region": "Kahramanmaraş, Türkiye",
        "event_date": "2023-02-06",
    },
    {
        "pair_id": "nepal-2015-kathmandu-03",
        "label": "Nepal 2015 — Kathmandu Valley Sector 03",
        "region": "Kathmandu, Nepal",
        "event_date": "2015-04-25",
    },
]

# In-memory job store (replace with Redis/DB + real model worker when ready)
JOBS: Dict[str, Dict[str, Any]] = {}


class CreateJobRequest(BaseModel):
    pair_id: str


def _load_template_result(
    job_id: str,
    pair_id: str,
    before_id: str,
    after_id: str,
) -> Dict[str, Any]:
    if FIXTURE_PATH.exists():
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    else:
        data = {
            "schema_version": "1.0.0",
            "model_version": "starter-pipeline-v0.2",
            "counts": {
                "total": 0,
                "no_apparent_damage": 0,
                "damaged": 0,
                "destroyed": 0,
            },
            "buildings": {"type": "FeatureCollection", "features": []},
        }

    result = copy.deepcopy(data)
    result["is_fixture"] = False
    result["job_id"] = job_id
    result["pair_id"] = pair_id
    result["status"] = "completed"
    result["error"] = None
    result["model_version"] = "starter-inference-v0.2"
    result["image_ids"] = {"before": before_id, "after": after_id}
    return result


async def _simulate_inference_worker(
    job_id: str,
    pair_id: str,
    before_id: str,
    after_id: str,
) -> None:
    """Simulates queued -> running -> completed stages so frontend polling works end-to-end."""
    try:
        await asyncio.sleep(1.2)
        if job_id not in JOBS:
            return
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["progress"] = 0.45

        await asyncio.sleep(1.5)
        if job_id not in JOBS:
            return
        JOBS[job_id]["progress"] = 0.85

        await asyncio.sleep(1.0)
        if job_id not in JOBS:
            return

        result = _load_template_result(job_id, pair_id, before_id, after_id)
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["progress"] = 1.0
        JOBS[job_id]["result"] = result
    except Exception as exc:  # pragma: no cover
        if job_id in JOBS:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(exc)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "inference_ready": True}


@app.get("/pairs")
def list_pairs() -> List[Dict[str, str]]:
    return PREPARED_PAIRS


@app.post("/jobs")
async def create_prepared_job(payload: CreateJobRequest) -> Dict[str, Any]:
    pair_ids = {p["pair_id"] for p in PREPARED_PAIRS}
    if payload.pair_id not in pair_ids:
        raise HTTPException(status_code=404, detail=f"Unknown pair_id: {payload.pair_id}")

    job_id = f"job-{uuid.uuid4().hex[:8]}"
    JOBS[job_id] = {
        "job_id": job_id,
        "pair_id": payload.pair_id,
        "status": "queued",
        "progress": 0.1,
        "error": None,
        "result": None,
    }
    asyncio.create_task(
        _simulate_inference_worker(
            job_id=job_id,
            pair_id=payload.pair_id,
            before_id=f"{payload.pair_id}_pre.tif",
            after_id=f"{payload.pair_id}_post.tif",
        )
    )
    return {
        "job_id": job_id,
        "pair_id": payload.pair_id,
        "status": "queued",
        "progress": 0.1,
        "error": None,
    }


@app.post("/jobs/upload")
async def create_upload_job(
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...),
    pair_id: Optional[str] = Form(None),
) -> Dict[str, Any]:
    resolved_pair_id = (
        pair_id.strip()
        if pair_id and pair_id.strip()
        else f"upload-{uuid.uuid4().hex[:6]}"
    )
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    # Read file headers/bytes to validate non-empty uploads
    before_bytes = await before_image.read()
    after_bytes = await after_image.read()
    if not before_bytes or not after_bytes:
        raise HTTPException(status_code=400, detail="Both before and after files must be non-empty.")

    JOBS[job_id] = {
        "job_id": job_id,
        "pair_id": resolved_pair_id,
        "status": "queued",
        "progress": 0.1,
        "error": None,
        "result": None,
    }
    asyncio.create_task(
        _simulate_inference_worker(
            job_id=job_id,
            pair_id=resolved_pair_id,
            before_id=before_image.filename or "before_upload.tif",
            after_id=after_image.filename or "after_upload.tif",
        )
    )
    return {
        "job_id": job_id,
        "pair_id": resolved_pair_id,
        "status": "queued",
        "progress": 0.1,
        "error": None,
    }


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return {
        "job_id": job["job_id"],
        "pair_id": job["pair_id"],
        "status": job["status"],
        "progress": job["progress"],
        "error": job["error"],
    }


@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if job["status"] != "completed" or not job["result"]:
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is currently '{job['status']}', result not ready.",
        )
    return job["result"]


@app.get("/jobs/{job_id}/export.{fmt}")
def export_job_report(job_id: str, fmt: str) -> Response:
    job = JOBS.get(job_id)
    if not job or job["status"] != "completed" or not job["result"]:
        raise HTTPException(status_code=404, detail=f"Completed result not found for {job_id}")

    buildings = job["result"].get("buildings", {})
    if fmt == "geojson":
        content = json.dumps(buildings, indent=2)
        return Response(
            content=content,
            media_type="application/geo+json",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.geojson"'},
        )

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "building_id",
                "object_kind",
                "footprint_source",
                "native_class",
                "display_category",
                "suggested_tier",
                "p_no_damage",
                "p_minor",
                "p_major",
                "p_destroyed",
            ]
        )
        for feat in buildings.get("features", []):
            props = feat.get("properties", {})
            probs = props.get("native_probabilities", [0, 0, 0, 0])
            writer.writerow(
                [
                    props.get("building_id", ""),
                    props.get("object_kind", ""),
                    props.get("footprint_source", ""),
                    props.get("native_class", ""),
                    props.get("display_category", ""),
                    props.get("suggested_tier", ""),
                    *probs,
                ]
            )
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.csv"'},
        )

    raise HTTPException(status_code=400, detail=f"Unsupported export format: {fmt}")
