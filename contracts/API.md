# Shared interfaces — version 0.1 draft

Owners: Students 2/3 agree model outputs; Students 3/4 agree API payloads. Update this document and a matching example in the same PR as an interface change. Only `/health` currently exists; the routes below are the implementation contract, not implemented endpoints.

## Job API

| Method / path | Purpose |
|---|---|
| `POST /jobs` | Validate a prepared pair or paired GeoTIFF upload; return job ID and queued status |
| `GET /jobs/{job_id}` | Return queued/running/completed/failed state and a user-readable error when failed |
| `GET /jobs/{job_id}/buildings` | Return GeoJSON building/group results, four native probabilities, display category and suggested tier |
| `GET /jobs/{job_id}/exports/csv` | Download matching result rows |
| `GET /jobs/{job_id}/exports/geojson` | Download matching geographic features |

One inference job at a time. Student 3 defines the multipart field names/prepared-example request discriminant before upload implementation; add a request example here. Do not silently mix raw source masks into these requests.

## Records

Input pair: pair/image IDs, before/after paths, dimensions, CRS, affine transform, provenance. Accepted raw images are same-grid RGB GeoTIFF pairs <=4096×4096; prepared PNG examples require a validated geography sidecar.

Result: job ID, pair ID, model version, explicit fixture flag, GeoJSON FeatureCollection, source image IDs and counts. Each feature has a unique region/building ID, pixel geometry, geographic geometry in WGS84 longitude/latitude order, object kind (building/group), footprint source (predicted/reference), four native probabilities in no/minor/major/destroyed order, native class, grouped display probabilities/category and suggested inspection tier. Add before/after crop URLs when the backend can serve them.

Map categories: no apparent damage / damaged / destroyed. Compute damaged probability by summing minor+major **before** display argmax. Quantitative evaluation remains four-class. Tier ordering is lower/medium/high; within-tier records tie. Probability is not physical damage percentage or a structural-safety finding. Reference features and fixtures must never be represented as genuine predictions.

CSV and GeoJSON must contain the same IDs/counts as API/map results. CSV location uses a point inside the polygon plus a map link. Empty predictions return an empty collection and zero counts; they do not crash the application.

`examples/result.fixture.json` contains invented developer data for interface work only. Its job ID/model version/fixture flag identify it clearly. It must not be included in reported experimental results or served as the default response to real inference requests.
