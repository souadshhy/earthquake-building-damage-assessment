# Shared interfaces — version 0.1

Owners are Students 2/3 for inference and Students 3/4 for HTTP payloads. The backend implements the routes below. Genuine inference requires Student 2's configured provider and trained checkpoint. Update examples with interface changes. Teammate integration review is pending.

## Job API

| Method / path | Purpose |
|---|---|
| `GET /health` | Report service and genuine inference readiness |
| `GET /pairs` | List registered prepared examples and rejected IDs/reasons |
| `POST /jobs` | Validate a prepared pair or paired GeoTIFF upload; return job ID and queued status |
| `GET /jobs/{job_id}` | Return queued/running/completed/failed state and a user-readable error when failed |
| `GET /jobs/{job_id}/buildings` | Return GeoJSON building/group results, four native probabilities, display category and suggested tier |
| `GET /jobs/{job_id}/exports/csv` | Download matching result rows |
| `GET /jobs/{job_id}/exports/geojson` | Download matching geographic features |
| `GET /jobs/{job_id}/crops/{region_index}/{selector}` | Serve a generated PNG preview; selector is `before` or `after` |

One inference job runs at a time. SQLite stores status and disk stores inputs/artifacts. One process owns each runtime directory. Interrupted running jobs become failed on restart; queued jobs resume when a provider is available. Completed jobs remain downloadable.

Prepared requests use `Content-Type: application/json` and `{"input_type":"prepared","pair_id":"haiti-earthquake_000001"}`. IDs must appear in `GET /pairs`. The server resolves image paths. Extra JSON fields are rejected. See `examples/prepared.request.json`.

Uploads use `multipart/form-data` with exactly three fields, `input_type=upload`, `before` file and `after` file. Source filenames are ignored. The complete request limit is 128 MiB, enforced while streaming. See `examples/upload.request.txt`.

Accepted images are three-band uint8 RGB with valid geography and dimensions up to 4096×4096. GeoTIFFs with nodata require preparation, as does other radiometry. Prepared RGB PNGs preserve RGB values including transparent-color pixels, matching the existing training loader. Before/after grids must match exactly. Prepared PNGs need sidecar CRS, affine, and finite internal consistency error <=1 m. Registry discovery checks headers; submission also decodes pixels and checks GeoTIFF validity masks.

Successful submission returns HTTP 202 with `job_id`, `pair_id`, `status=queued`, ISO UTC `created_at`/`updated_at`, `error=null`, and `model_version=null`. Status retrieval returns these fields with the current state, failure text, and completed model identity. See `examples/job.queued.json` and `examples/job.failed.json`.

HTTP outcomes are 404 for unknown jobs/crops, 409 for results/exports/crops before completion, 413 for oversized uploads, 422 for invalid requests/images, and 503 when genuine inference is unavailable. Failed jobs remain visible through status; create a new job to retry. Empty detections complete successfully.

## Records

Input pair: pair/image IDs, before/after paths, dimensions, CRS, affine transform, provenance. Accepted raw images are same-grid RGB GeoTIFF pairs <=4096×4096; prepared PNG examples require a validated geography sidecar.

`GET /jobs/{job_id}/buildings` returns the existing result envelope, including `schema_version`, job ID, pair ID, model version, fixture flag, `buildings` FeatureCollection, source image IDs, counts, and geography provenance. GeoJSON downloads return the FeatureCollection directly. Each feature has a unique `building_id`, pixel Polygon, WGS84 geometry, `object_kind` (`building` or `building_group`), `footprint_source=predicted`, four native probabilities, native class, grouped display values, tier, crop window and `crop_urls.before`/`crop_urls.after`. Follow the returned URLs, since indices are job-local. For the frontend proxy, prefix returned root-relative URLs with `/api`.

Native class strings are `no-damage`, `minor-damage`, `major-damage`, `destroyed`. Wire display categories/count keys are `no_apparent_damage`, `damaged`, `destroyed`. The backend translates the label helper's `destroyed_or_collapsed` to `destroyed`. Ties use the first class in the documented order.

Map categories: no apparent damage / damaged / destroyed. Compute damaged probability by summing minor+major **before** display argmax. Quantitative evaluation remains four-class. Tier ordering is lower/medium/high; within-tier records tie. Probability is not physical damage percentage or a structural-safety finding. Reference features and fixtures must never be represented as genuine predictions.

Exports contain the whole completed job. Frontend filters affect visible counts only; show the job total and label downloads “Download whole job”. CSV and GeoJSON contain the same IDs/counts as the unfiltered API result. CSV includes four native and three display probabilities, model/image identity, group/footprint provenance, an interior longitude/latitude point and map link. Empty predictions return an empty collection, zero counts, and a header-only CSV.

`examples/result.fixture.json` contains invented developer data for interface work only. Its job ID/model version/fixture flag identify it clearly. It must not be included in reported experimental results or served as the default response to real inference requests.

## Student 2 inference provider

Set `QUAKE_INFERENCE=package.module:provider` before starting the service. `provider` is a callable object with `check_ready()` and `__call__(pair)`. Startup calls `check_ready()` to load/check trained artifacts and fail readiness with an explanation if unavailable. The callable runs in the serial background worker. It must use genuine detector/classifier output and return the contract below. See `examples/inference.output.fixture.json` for synthetic shape only.

Input `pair` contains `pair_id`, absolute server-side `before`/`after` paths, image IDs, width, height, CRS, six affine coefficients in `(a,b,c,d,e,f)` order, and provenance.

Output contains `model_version` (include checkpoint identity/hash), matching `image_ids`, and a `regions` list. Each region contains unique string `building_id`, `object_kind`, valid in-bounds pixel `Polygon`, four finite probabilities summing to one in no/minor/major/destroyed order, and integer `crop_box=[left,top,right,bottom]`.

Student 2 owns probability thresholding, connected regions, polygon extraction, classification and preprocessing. The crop box is the polygon bounding box plus 20% context per side, rounded outward, matching `quake.crops.crop_pair`. Preview images use the same PIL crop, black outside-image padding, bilinear resize to 224×224, before normalization. Student 1/2 must review this existing padding behavior against the team plan before model integration. Invalid model records fail the job with an explanation; records are never silently dropped.

The backend validates output, converts geography, groups display probabilities and writes exports. Existing classifier checkpoint loading rejects feasibility-only weights by default. Student 2's readiness check must preserve that rule and verify the class order, paired mode, and pinned detector provenance. No provider or trained damage checkpoint is supplied by this backend implementation.
