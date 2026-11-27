import { FormEvent, useEffect, useState } from "react";
import {
  HealthResponse,
  JobStatusResponse,
  PreparedPair,
  fetchHealth,
  fetchJobResult,
  fetchJobStatus,
  fetchPreparedPairs,
  getExportUrl,
  submitPreparedPairJob,
  submitUploadJob,
} from "../api/client";
import { AssessmentResult } from "../types/assessment";

export type DataSourceMode = "fixture" | "live";

interface BackendJobPanelProps {
  mode: DataSourceMode;
  onModeChange: (mode: DataSourceMode) => void;
  activeAssessment: AssessmentResult | null;
  visibleCount: number;
  onLiveResultLoaded: (result: AssessmentResult) => void;
}

export default function BackendJobPanel({
  mode,
  onModeChange,
  activeAssessment,
  visibleCount,
  onLiveResultLoaded,
}: BackendJobPanelProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [pairs, setPairs] = useState<PreparedPair[]>([]);
  const [pairsError, setPairsError] = useState<string | null>(null);
  const [pairsLoading, setPairsLoading] = useState(false);
  const [selectedPairId, setSelectedPairId] = useState<string>("");
  const [submissionTab, setSubmissionTab] = useState<"prepared" | "upload">(
    "prepared"
  );
  const [beforeFile, setBeforeFile] = useState<File | null>(null);
  const [afterFile, setAfterFile] = useState<File | null>(null);

  const [activeJob, setActiveJob] = useState<JobStatusResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "live") return;
    let cancelled = false;

    async function loadBackendMeta() {
      setPairsLoading(true);
      try {
        const h = await fetchHealth();
        if (!cancelled) {
          setHealth(h);
          setHealthError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setHealth(null);
          setHealthError(
            err instanceof Error
              ? err.message
              : "Backend unreachable on http://127.0.0.1:8000"
          );
        }
      }

      try {
        const registry = await fetchPreparedPairs();
        if (!cancelled) {
          setPairs(registry.pairs);
          setPairsError(null);
          setSelectedPairId((prev) =>
            registry.pairs.some((p) => p.pair_id === prev)
              ? prev
              : (registry.pairs[0]?.pair_id ?? "")
          );
        }
      } catch (err) {
        if (!cancelled) {
          setPairs([]);
          setSelectedPairId("");
          setPairsError(
            err instanceof Error
              ? err.message
              : "Failed to load prepared pairs from registry."
          );
        }
      } finally {
        if (!cancelled) setPairsLoading(false);
      }
    }

    loadBackendMeta();
    return () => {
      cancelled = true;
    };
  }, [mode]);

  useEffect(() => {
    if (
      mode !== "live" ||
      !activeJob ||
      (activeJob.status !== "queued" && activeJob.status !== "running")
    ) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const statusRes = await fetchJobStatus(activeJob.job_id);
        setActiveJob(statusRes);

        if (statusRes.status === "completed") {
          const result = await fetchJobResult(statusRes.job_id);
          onLiveResultLoaded(result);
        } else if (statusRes.status === "failed") {
          setJobError(statusRes.error || "Inference job failed on backend.");
        }
      } catch (err) {
        setJobError(
          err instanceof Error ? err.message : "Error polling job status."
        );
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [mode, activeJob, onLiveResultLoaded]);

  const isPolling =
    activeJob?.status === "queued" || activeJob?.status === "running";
  const inferenceReady = Boolean(health?.inference_ready);
  const canSubmitPrepared =
    inferenceReady && !submitting && !isPolling && Boolean(selectedPairId);
  const canSubmitUpload =
    inferenceReady &&
    !submitting &&
    !isPolling &&
    Boolean(beforeFile && afterFile);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!inferenceReady) return;
    setJobError(null);
    setSubmitting(true);

    try {
      let job: JobStatusResponse;
      if (submissionTab === "prepared") {
        if (!selectedPairId) {
          setJobError("No valid prepared pair selected.");
          setSubmitting(false);
          return;
        }
        job = await submitPreparedPairJob(selectedPairId);
      } else {
        if (!beforeFile || !afterFile) {
          setJobError("Please select both a Before and After GeoTIFF file.");
          setSubmitting(false);
          return;
        }
        job = await submitUploadJob({
          beforeFile,
          afterFile,
        });
      }

      setActiveJob(job);
      if (job.status === "completed") {
        const result = await fetchJobResult(job.job_id);
        onLiveResultLoaded(result);
      } else if (job.status === "failed") {
        setJobError(job.error || "Job failed immediately.");
      }
    } catch (err) {
      setJobError(
        err instanceof Error ? err.message : "Failed to submit assessment job."
      );
    } finally {
      setSubmitting(false);
    }
  }

  function handleFixtureExport(format: "geojson" | "csv") {
    if (!activeAssessment) return;
    let content = "";
    let mime = "application/json";
    if (format === "geojson") {
      content = JSON.stringify(activeAssessment.buildings, null, 2);
    } else {
      mime = "text/csv";
      const header = [
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
      ].join(",");
      const rows = activeAssessment.buildings.features.map((f) => {
        const p = f.properties;
        return [
          p.building_id,
          p.object_kind,
          p.footprint_source,
          p.native_class,
          p.display_category,
          p.suggested_tier,
          ...p.native_probabilities,
        ].join(",");
      });
      content = [header, ...rows].join("\n");
    }

    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeAssessment.job_id}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const jobTotalCount = activeAssessment?.counts.total ?? 0;

  return (
    <section className="backend-panel" aria-label="Data source and exports">
      <div className="backend-panel-top">
        <div className="mode-toggle" role="group" aria-label="Data source mode">
          <button
            type="button"
            className={`mode-btn ${mode === "fixture" ? "mode-btn-active" : ""}`}
            onClick={() => onModeChange("fixture")}
          >
            Fixture Mode (Demo)
          </button>
          <button
            type="button"
            className={`mode-btn ${mode === "live" ? "mode-btn-active" : ""}`}
            onClick={() => onModeChange("live")}
          >
            Live Backend Mode
          </button>
        </div>

        <div className="export-group">
          {activeAssessment ? (
            <>
              <span className="muted-small">
                Download whole job ({jobTotalCount} total &middot; {visibleCount}{" "}
                visible):
              </span>
              {activeAssessment.is_fixture ? (
                <>
                  <button
                    type="button"
                    className="export-btn"
                    onClick={() => handleFixtureExport("geojson")}
                  >
                    GeoJSON
                  </button>
                  <button
                    type="button"
                    className="export-btn"
                    onClick={() => handleFixtureExport("csv")}
                  >
                    CSV
                  </button>
                </>
              ) : (
                <>
                  <a
                    className="export-btn"
                    href={getExportUrl(activeAssessment.job_id, "geojson")}
                    download
                  >
                    GeoJSON
                  </a>
                  <a
                    className="export-btn"
                    href={getExportUrl(activeAssessment.job_id, "csv")}
                    download
                  >
                    CSV
                  </a>
                </>
              )}
            </>
          ) : (
            <span className="muted-small">
              Download whole job: unavailable until a live job completes
            </span>
          )}
        </div>
      </div>

      {mode === "live" && (
        <div className="live-controls">
          <div className="health-strip">
            {health ? (
              <span
                className={`status-pill ${
                  health.inference_ready ? "status-ok" : "status-err"
                }`}
              >
                API Connected &middot; Inference Ready:{" "}
                <strong>{health.inference_ready ? "Yes" : "No"}</strong>
                {!health.inference_ready && health.inference_reason
                  ? ` — ${health.inference_reason}`
                  : ""}
              </span>
            ) : (
              <span className="status-pill status-err">
                API Disconnected: {healthError ?? "Checking..."}
              </span>
            )}

            {activeJob && (
              <span className={`status-pill status-job-${activeJob.status}`}>
                Job <code>{activeJob.job_id}</code>:{" "}
                <strong>{activeJob.status.toUpperCase()}</strong>
                {typeof activeJob.progress === "number"
                  ? ` (${Math.round(activeJob.progress * 100)}%)`
                  : ""}
              </span>
            )}
          </div>

          <form className="job-form" onSubmit={handleSubmit}>
            <div className="sub-tabs">
              <button
                type="button"
                className={`sub-tab ${
                  submissionTab === "prepared" ? "sub-tab-active" : ""
                }`}
                onClick={() => setSubmissionTab("prepared")}
              >
                Prepared Pair
              </button>
              <button
                type="button"
                className={`sub-tab ${
                  submissionTab === "upload" ? "sub-tab-active" : ""
                }`}
                onClick={() => setSubmissionTab("upload")}
              >
                Upload GeoTIFF Pair
              </button>
            </div>

            {submissionTab === "prepared" ? (
              <div className="job-form-row">
                {pairsError ? (
                  <span className="job-error" role="alert">
                    Registry error: {pairsError}
                  </span>
                ) : pairsLoading ? (
                  <span className="muted-small">Loading prepared pairs...</span>
                ) : pairs.length === 0 ? (
                  <span className="muted-small">
                    No valid prepared pairs registered on backend.
                  </span>
                ) : (
                  <select
                    value={selectedPairId}
                    onChange={(e) => setSelectedPairId(e.target.value)}
                    disabled={submitting || isPolling}
                  >
                    {pairs.map((p) => (
                      <option key={p.pair_id} value={p.pair_id}>
                        {p.label ?? p.pair_id}
                        {p.width && p.height ? ` (${p.width}×${p.height})` : ""}
                      </option>
                    ))}
                  </select>
                )}
                <button
                  type="submit"
                  className="primary-btn"
                  disabled={!canSubmitPrepared}
                >
                  {submitting
                    ? "Submitting..."
                    : isPolling
                      ? "Running Inference..."
                      : "Run Assessment"}
                </button>
              </div>
            ) : (
              <div className="job-form-row">
                <label className="file-input-label">
                  <span>Pre-Event (.tif):</span>
                  <input
                    type="file"
                    accept=".tif,.tiff"
                    onChange={(e) => setBeforeFile(e.target.files?.[0] ?? null)}
                    disabled={submitting || isPolling}
                  />
                </label>
                <label className="file-input-label">
                  <span>Post-Event (.tif):</span>
                  <input
                    type="file"
                    accept=".tif,.tiff"
                    onChange={(e) => setAfterFile(e.target.files?.[0] ?? null)}
                    disabled={submitting || isPolling}
                  />
                </label>
                <button
                  type="submit"
                  className="primary-btn"
                  disabled={!canSubmitUpload}
                >
                  {submitting
                    ? "Uploading..."
                    : isPolling
                      ? "Running Inference..."
                      : "Upload & Assess"}
                </button>
              </div>
            )}
          </form>

          {jobError && (
            <p className="job-error" role="alert">
              {jobError}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
