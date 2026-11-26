"""Backend contract tests use explicit test inference, never real accuracy claims."""
import csv
import io
import math
from pathlib import Path
from threading import Event, Lock
import time
import types
import sys

from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import pytest
import rasterio
from affine import Affine
from shapely.geometry import Point, shape

from backend.app import create_app
from backend.inputs import PairRegistry, validate_pair
from backend.jobs import Jobs, configured_inference
from backend.results import build_results
from quake.io import write_json


def geotiff(path, width=40, height=40, transform=None, crs="EPSG:4326"):
    with rasterio.open(path, "w", driver="GTiff", width=width, height=height, count=3,
                       dtype="uint8", crs=crs, transform=transform or Affine(.001, 0, -72, 0, -.001, 19)) as source:
        source.write(np.full((3, height, width), 128, dtype=np.uint8))


@pytest.fixture
def prepared(tmp_path):
    data = tmp_path / "data/haitibrd_prepared_v1"
    data.mkdir(parents=True)
    for selector in ("before", "after"):
        geotiff(data / f"{selector}.tif")
    row = {"pair_id": "test-pair", "before": str(data / "before.tif"), "after": str(data / "after.tif"),
           "width": 40, "height": 40, "crs": "EPSG:4326", "transform": [.001, 0, -72, 0, -.001, 19],
           "contains_severity_labels": False}
    write_json(data / "demo_pairs.json", [row])
    return tmp_path, row


def prediction(pair):
    return {"model_version": "test-provider-no-trained-model", "image_ids": pair["image_ids"], "regions": [{
        "building_id": 'region,"one"', "object_kind": "building_group",
        "pixel_geometry": {"type": "Polygon", "coordinates": [
            [[10, 10], [30, 10], [30, 30], [10, 30], [10, 10]],
            [[15, 15], [15, 25], [25, 25], [25, 15], [15, 15]]]},
        "native_probabilities": [.4, .25, .25, .1], "crop_box": [6, 6, 34, 34]}]}


def finished(client, job_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(.01)
    pytest.fail("Job failed to reach a terminal state")


def submit(client):
    response = client.post("/jobs", json={"input_type": "prepared", "pair_id": "test-pair"})
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"
    return response.json()["job_id"]


def test_end_to_end_exports_crops_and_restart(prepared):
    root, row = prepared
    with TestClient(create_app(root, inference=prediction)) as client:
        assert client.get("/health").json()["inference_ready"]
        assert client.get("/pairs").json()["pairs"][0]["pair_id"] == "test-pair"
        job_id = submit(client)
        assert finished(client, job_id)["status"] == "completed"
        result = client.get(f"/jobs/{job_id}/buildings").json()
        feature = result["buildings"]["features"][0]
        props = feature["properties"]
        assert result["counts"] == {"total": 1, "no_apparent_damage": 0, "damaged": 1, "destroyed": 0}
        assert props["native_class"] == "no-damage"
        assert props["display_category"] == "damaged"
        assert props["suggested_tier"] == "medium"
        assert feature["geometry"]["coordinates"][0][0] == pytest.approx([-71.99, 18.99])
        assert len(feature["geometry"]["coordinates"]) == 2
        rows = list(csv.DictReader(io.StringIO(client.get(f"/jobs/{job_id}/exports/csv").text)))
        geojson = client.get(f"/jobs/{job_id}/exports/geojson").json()
        assert [r["building_id"] for r in rows] == [f["properties"]["building_id"] for f in geojson["features"]]
        assert shape(feature["geometry"]).contains(Point(float(rows[0]["longitude"]), float(rows[0]["latitude"])))
        assert rows[0]["model_version"] == result["model_version"]
        assert rows[0]["before_image_id"] == result["image_ids"]["before"]
        for selector, url in props["crop_urls"].items():
            response = client.get(url)
            assert response.status_code == 200
            image = Image.open(io.BytesIO(response.content))
            assert image.size == (224, 224)
        assert client.get(f"/jobs/{job_id}/crops/55/before").status_code == 404
    with TestClient(create_app(root, inference=prediction)) as client:
        assert client.get(f"/jobs/{job_id}").json()["status"] == "completed"
        assert client.get(f"/jobs/{job_id}/exports/csv").status_code == 200


@pytest.mark.parametrize("empty", [True, False])
def test_empty_and_failed_inference(prepared, empty):
    root, _ = prepared
    def provider(pair):
        if not empty:
            raise RuntimeError("model failed to load")
        return prediction(pair) | {"regions": []}
    with TestClient(create_app(root, inference=provider)) as client:
        job_id = submit(client)
        status = finished(client, job_id)
        if empty:
            result = client.get(f"/jobs/{job_id}/buildings").json()
            assert result["counts"]["total"] == 0
            assert result["buildings"]["features"] == []
            assert list(csv.DictReader(io.StringIO(client.get(f"/jobs/{job_id}/exports/csv").text))) == []
        else:
            assert status["status"] == "failed"
            assert "model failed to load" in status["error"]
            assert client.get(f"/jobs/{job_id}/buildings").status_code == 409


def test_serial_submission_and_pending_result(prepared):
    root, _ = prepared
    entered, release = Event(), Event()
    mutex = Lock()
    active, maximum, calls = 0, 0, 0
    def provider(pair):
        nonlocal active, maximum, calls
        with mutex:
            active += 1
            maximum = max(maximum, active)
            calls += 1
        entered.set()
        assert release.wait(10)
        with mutex:
            active -= 1
        return prediction(pair)
    with TestClient(create_app(root, inference=provider)) as client:
        try:
            first = submit(client)
            assert entered.wait(5)
            second = submit(client)
            assert client.get(f"/jobs/{first}/buildings").status_code == 409
            assert client.get(f"/jobs/{second}").json()["status"] == "queued"
        finally:
            release.set()
        assert finished(client, first)["status"] == "completed"
        assert finished(client, second)["status"] == "completed"
        assert maximum == 1 and calls == 2


def test_restart_recovers_queued_marks_interrupted_and_excludes_second_worker(prepared):
    root, row = prepared
    directory = root / "jobs"
    jobs = Jobs(directory, None)
    jobs.start()
    try:
        interrupted = jobs.create(validate_pair(row))["job_id"]
        queued = jobs.create(validate_pair(row))["job_id"]
        with jobs.connect() as connection:
            connection.execute("UPDATE jobs SET status='running' WHERE job_id=?", (interrupted,))
        with pytest.raises(RuntimeError, match="active backend"):
            Jobs(directory, None).start()
    finally:
        jobs.close()
    with TestClient(create_app(root, runtime=directory, inference=prediction)) as client:
        assert client.get(f"/jobs/{interrupted}").json()["status"] == "failed"
        assert finished(client, queued)["status"] == "completed"


def test_readiness_and_request_errors(prepared, monkeypatch):
    root, _ = prepared
    monkeypatch.delenv("QUAKE_INFERENCE", raising=False)
    with TestClient(create_app(root)) as client:
        assert not client.get("/health").json()["inference_ready"]
        assert client.post("/jobs", json={"input_type": "prepared", "pair_id": "test-pair"}).status_code == 503
    with TestClient(create_app(root, inference=prediction)) as client:
        for payload in ({}, {"input_type": "prepared", "pair_id": "absent"},
                        {"input_type": "prepared", "pair_id": "test-pair", "severity": 3}):
            assert client.post("/jobs", json=payload).status_code == 422
        assert client.post("/jobs", content="{bad", headers={"content-type": "application/json"}).status_code == 422
        assert client.get("/jobs/absent").status_code == 404
        assert set(client.get("/openapi.json").json()["paths"]["/jobs"]["post"]["requestBody"]["content"]) == {"application/json", "multipart/form-data"}
    monkeypatch.setenv("QUAKE_INFERENCE", "backend.absent:predict")
    assert configured_inference()[0] is None


def test_configured_provider_uses_normal_startup(prepared, monkeypatch):
    root, _ = prepared
    class Provider:
        def __init__(self):
            self.checked = False

        def check_ready(self):
            self.checked = True

        def __call__(self, pair):
            assert self.checked
            return prediction(pair)

    provider = Provider()
    module = types.ModuleType("test_backend_provider")
    module.provider = provider
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setenv("QUAKE_INFERENCE", "test_backend_provider:provider")
    with TestClient(create_app(root)) as client:
        assert provider.checked
        job_id = submit(client)
        assert finished(client, job_id)["status"] == "completed"


def test_upload_and_upload_limit(prepared, monkeypatch):
    root, row = prepared
    files = {key: (f"{key}.tif", Path(row[key]).read_bytes(), "image/tiff") for key in ("before", "after")}
    with TestClient(create_app(root, inference=prediction)) as client:
        response = client.post("/jobs", data={"input_type": "upload"}, files=files)
        assert response.status_code == 202, response.text
        assert finished(client, response.json()["job_id"])["status"] == "completed"
        assert client.post("/jobs", data={"input_type": "upload"}, files={"before": files["before"]}).status_code == 422
        monkeypatch.setattr("backend.app.MAX_UPLOAD_BYTES", 100)
        assert client.post("/jobs", data={"input_type": "upload"}, files=files).status_code == 413


@pytest.mark.parametrize("change, message", [
    ({"contains_severity_labels": True}, "imagery only"),
    ({"width": 99}, "dimensions"),
    ({"transform": [0, 0, 0, 0, 0, 0]}, "manifest geography"),
])
def test_manifest_validation(prepared, change, message):
    _, row = prepared
    with pytest.raises(ValueError, match=message):
        validate_pair(row | change)


def test_invalid_grids_crs_dimensions_and_nodata(prepared):
    _, row = prepared
    for kwargs in ({"transform": Affine(.002, 0, -72, 0, -.001, 19)}, {"crs": None}, {"width": 4097}):
        geotiff(row["after"], **kwargs)
        with pytest.raises(ValueError):
            validate_pair(row, upload=True)
    geotiff(row["after"])
    with rasterio.open(row["after"], "r+") as source:
        source.nodata = 0
    with pytest.raises(ValueError, match="nodata"):
        validate_pair(row)


def test_rotated_projected_grid_and_edge_crop(prepared):
    root, row = prepared
    transform = Affine(2, .1, 500000, .1, -2, 2000000)
    for selector in ("before", "after"):
        geotiff(row[selector], transform=transform, crs="EPSG:32618")
    row.update(crs="EPSG:32618", transform=list(transform)[:6])
    pair = validate_pair(row)
    output = prediction(pair)
    region = output["regions"][0]
    region["pixel_geometry"] = {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}
    region["crop_box"] = [-2, -2, 12, 12]
    result = build_results("edge", pair, output, root / "edge")
    lon, lat = result["buildings"]["features"][0]["geometry"]["coordinates"][0][0]
    assert -76 < lon < -74 and 17 < lat < 19
    image = Image.open(root / "edge/crop-0-before.png")
    assert image.getpixel((0, 0)) == (0, 0, 0)


def test_png_sidecar_and_registry_rejections(prepared):
    root, row = prepared
    for selector in ("before", "after"):
        path = root / f"{selector}.png"
        Image.new("RGB", (40, 40)).save(path, transparency=(0, 0, 0))
        row[selector] = str(path)
    with pytest.raises(ValueError, match="validated geography"):
        validate_pair(row)
    row["transform_internal_error_m"] = .01
    assert validate_pair(row)["crs"] == "EPSG:4326"
    with pytest.raises(ValueError, match="GeoTIFF"):
        validate_pair(row, upload=True)
    write_json(root / "data/haitibrd_prepared_v1/demo_pairs.json", [row, row | {"pair_id": "bad", "geography_issue": "failed"}])
    registry = PairRegistry(root)
    assert list(registry.records) == ["test-pair"]
    assert registry.rejected[0]["pair_id"] == "bad"


@pytest.mark.parametrize("probabilities, category, tier", [
    ([.1, .1, .2, .6], "destroyed", "high"),
    ([.7, .1, .1, .1], "no_apparent_damage", "lower"),
    ([.4, .25, .25, .1], "damaged", "medium"),
])
def test_wire_category_and_tier_mapping(prepared, probabilities, category, tier):
    root, row = prepared
    pair = validate_pair(row)
    output = prediction(pair)
    output["regions"][0]["native_probabilities"] = probabilities
    result = build_results("mapping", pair, output, root / "mapping")
    properties = result["buildings"]["features"][0]["properties"]
    assert properties["display_category"] == category
    assert properties["suggested_tier"] == tier
    assert result["counts"][category] == 1


@pytest.mark.parametrize("mutation", ["duplicate", "probability", "bounds", "crop", "image_ids", "version"])
def test_bad_model_outputs_fail_instead_of_dropping_records(prepared, mutation):
    root, row = prepared
    pair = validate_pair(row)
    output = prediction(pair)
    region = output["regions"][0]
    if mutation == "duplicate":
        output["regions"].append(region.copy())
    elif mutation == "probability":
        region["native_probabilities"] = [math.nan, 0, 0, 1]
    elif mutation == "bounds":
        region["pixel_geometry"]["coordinates"][0][0][0] = -1
    elif mutation == "crop":
        region["crop_box"] = [0, 0, 10, 10]
    elif mutation == "image_ids":
        output["image_ids"] = {"before": "wrong", "after": "wrong"}
    else:
        output["model_version"] = ""
    with pytest.raises(ValueError):
        build_results("test", pair, output, root / "output")
