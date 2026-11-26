"""Local inspection API with explicit model readiness and persistent jobs."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
import shutil
from typing import Literal
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
import rasterio
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException
from starlette.exceptions import HTTPException as StarletteHTTPException

from quake.io import read_json
from .inputs import PairRegistry, validate_pair
from .jobs import Jobs, configured_inference

ROOT = Path(__file__).resolve().parents[1]
MAX_UPLOAD_BYTES = 128 * 1024 * 1024


class PreparedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_type: Literal["prepared"]
    pair_id: str


def create_app(root=ROOT, runtime=None, inference=None):
    root = Path(root)
    runtime = Path(runtime or os.environ.get("QUAKE_RUNTIME", root / "runtime/backend"))

    @asynccontextmanager
    async def lifespan(app):
        provider, reason = (inference, None) if inference is not None else configured_inference()
        registry = await run_in_threadpool(PairRegistry, root)
        jobs = Jobs(runtime, provider)
        await run_in_threadpool(jobs.start)
        app.state.registry, app.state.jobs = registry, jobs
        app.state.inference_reason = reason
        try:
            yield
        finally:
            await run_in_threadpool(jobs.close)

    app = FastAPI(title="Earthquake inspection API", version="0.2.0", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "inference_ready": app.state.jobs.inference is not None,
                "inference_reason": app.state.inference_reason}

    @app.get("/pairs")
    def pairs():
        registry = app.state.registry
        return {"pairs": [{key: row[key] for key in ("pair_id", "width", "height", "crs", "provenance")}
                          for row in registry.records.values()], "rejected": registry.rejected}

    @app.post("/jobs", status_code=202)
    async def create_job(request: Request):
        if app.state.jobs.inference is None:
            raise HTTPException(503, app.state.inference_reason)
        content_type = request.headers.get("content-type", "").split(";", 1)[0]
        if content_type == "application/json":
            try:
                submission = PreparedRequest.model_validate(await request.json())
            except ValueError as exc:
                raise HTTPException(422, "Expected input_type=prepared and a registered pair_id") from exc
            record = app.state.registry.records.get(submission.pair_id)
            if record is None:
                raise HTTPException(422, "Unknown or invalid prepared pair; see GET /pairs")
            try:
                pair = await run_in_threadpool(validate_pair, record)
            except (ValueError, TypeError, KeyError, OSError, rasterio.errors.RasterioError) as exc:
                raise HTTPException(422, f"Prepared pair validation failed: {exc}") from exc
            return await run_in_threadpool(app.state.jobs.create, pair)
        if content_type != "multipart/form-data":
            raise HTTPException(422, "Use prepared-pair JSON or multipart GeoTIFF uploads")
        job_id = uuid.uuid4().hex
        staging = runtime / ("upload-" + job_id)
        staging.mkdir(parents=True)
        total = 0
        oversized = False

        async def bounded_receive():
            nonlocal total, oversized
            message = await request.receive()
            total += len(message.get("body", b""))
            if total > MAX_UPLOAD_BYTES:
                oversized = True
                # Starlette closes temporary files when this parser exception is raised.
                raise MultiPartException("Upload exceeds 128 MiB request limit")
            return message

        bounded = Request(request.scope, receive=bounded_receive)
        try:
            async with bounded.form(max_files=2, max_fields=1) as form:
                if set(form) != {"input_type", "before", "after"} or len(form.multi_items()) != 3 or form.get("input_type") != "upload":
                    raise HTTPException(422, "Expected input_type=upload and before/after files")
                for selector in ("before", "after"):
                    upload = form[selector]
                    if not isinstance(upload, UploadFile):
                        raise HTTPException(422, "Before and after must be files")
                    with (staging / f"{selector}.tif").open("wb") as stream:
                        while chunk := await upload.read(1024 * 1024):
                            stream.write(chunk)
            pair = await run_in_threadpool(validate_pair, {
                "pair_id": "upload-" + job_id, "before": str(staging / "before.tif"),
                "after": str(staging / "after.tif")}, True)
            return await run_in_threadpool(app.state.jobs.create, pair, job_id)
        except StarletteHTTPException as exc:
            shutil.rmtree(staging)
            if oversized:
                raise HTTPException(413, "Upload exceeds 128 MiB request limit") from exc
            if exc.status_code == 400:
                raise HTTPException(422, exc.detail) from exc
            raise
        except (ValueError, TypeError, KeyError, OSError, rasterio.errors.RasterioError) as exc:
            shutil.rmtree(staging)
            raise HTTPException(422, f"Image validation failed: {exc}") from exc

    def get_job(job_id, completed=False):
        job = app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Unknown job")
        if completed and job["status"] != "completed":
            raise HTTPException(409, {"status": job["status"], "error": job["error"]})
        return job

    @app.get("/jobs/{job_id}")
    def job_status(job_id: str):
        return get_job(job_id)

    @app.get("/jobs/{job_id}/buildings")
    def buildings(job_id: str):
        get_job(job_id, completed=True)
        return read_json(runtime / job_id / "result.json")

    @app.get("/jobs/{job_id}/exports/{format}")
    def export(job_id: str, format: Literal["csv", "geojson"]):
        get_job(job_id, completed=True)
        return FileResponse(runtime / job_id / f"results.{format}",
                            media_type="text/csv" if format == "csv" else "application/geo+json",
                            filename=f"{job_id}.{format}")

    @app.get("/jobs/{job_id}/crops/{region_index}/{selector}")
    def crop(job_id: str, region_index: int, selector: Literal["before", "after"]):
        get_job(job_id, completed=True)
        path = runtime / job_id / f"crop-{region_index}-{selector}.png"
        if region_index < 0 or not path.is_file():
            raise HTTPException(404, "Unknown crop")
        return FileResponse(path, media_type="image/png")

    for route in app.routes:
        if route.path == "/jobs" and "POST" in route.methods:
            route.openapi_extra = {"requestBody": {"required": True, "content": {
                "application/json": {"schema": PreparedRequest.model_json_schema()},
                "multipart/form-data": {"schema": {"type": "object", "required": ["input_type", "before", "after"],
                    "properties": {"input_type": {"type": "string", "enum": ["upload"]},
                                   "before": {"type": "string", "format": "binary"},
                                   "after": {"type": "string", "format": "binary"}}}}
            }}}
    return app


app = create_app()
