import { FormEvent, useEffect, useState } from "react";
import {
  ApiError,
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
  activeAssessment: AssessmentResult;
  onLiveResultLoaded: (result: AssessmentResult) => void;
}

const DEFAULT_PAIRS: PreparedPair[] = [
  {
    pair_id: "haiti-2010-port-au-prince-01",
    label: "Haiti 2010 — Port-au-Prince Sector 01 (Prepared Pair)",
  },
];

export default function BackendJobPanel({
  mode,
  onModeChange,
  activeAssessment,
  onLiveResultLoaded,
}: BackendJobPanelProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [pairs, setPairs] = useState<PreparedPair[]>(DEFAULT_PAIRS);
  const [selectedPairId, setSelectedPairId] = useState<string>(
    DEFAULT_PAIRS[0].pair_id
  );
  const [submissionTab, setSubmissionTab] = useState<"prepared" | "upload">(
    "prepared"
  );
  const [beforeFile, setBeforeFile] = useState<File | null>(null);
  const [afterFile, setAfterFile] = useState<File | null>(null);
  const [customPairLabel, setCustomPairLabel] = useState<string>("");

  const [activeJob, setActiveJob] = useState<JobStatusResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  // Check backend health & prepared pairs whenever switching to live mode
  useEffect(() => {
    if (mode !== "live") return;
    let cancelled = false;

    async function loadBackendMeta() {
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
        const remotePairs = await fetchPreparedPairs();
        if (!cancelled && remotePairs.length > 0) {
          setPairs(remotePairs);
          setSelectedPairId(remotePairs[0].pair_id);
        }
      } catch {
        // Keep fallback prepared pair list if /pairs is not implemented yet
      }
    }

    loadBackendMeta();
    return () => {
      cancelled = true;
    };
  }, [mode]);

  // Poll queued/running jobs every 2 seconds until completed or failed
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

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setJobError(null);
    setSubmitting(true);

    try {
      let job: JobStatusResponse;
      if (submissionTab === "prepared") {
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
          pairLabel: customPairLabel,
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
      if (err instanceof ApiError && err.status === 404) {
        setJobError(
          "Backend job endpoint (POST /jobs) is not implemented yet on the FastAPI server."
        );
      } else {
        setJobError(
          err instanceof Error ? err.message : "Failed to submit assessment job."
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleFixtureExport(format: "geojson" | "csv") {
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

  const isPolling =
    activeJob?.status === "queued" || activeJob?.status === "running";

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
          <span className="muted-small">Export Report:</span>
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
        </div>
      </div>

      {mode === "live" && (
        <div className="live-controls">
          <div className="health-strip">
            {health ? (
              <span className="status-pill status-ok">
                API Connected &middot; Inference Ready:{" "}
                <strong>{health.inference_ready ? "Yes" : "No (Starter)"}</strong>
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
                <select
                  value={selectedPairId}
                  onChange={(e) => setSelectedPairId(e.target.value)}
                  disabled={submitting || isPolling}
                >
                  {pairs.map((p) => (
                    <option key={p.pair_id} value={p.pair_id}>
                      {p.label}
                    </option>
                  ))}
                </select>
                <button
                  type="submit"
                  className="primary-btn"
                  disabled={submitting || isPolling}
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
                <input
                  type="text"
                  placeholder="Optional pair label"
                  value={customPairLabel}
                  onChange={(e) => setCustomPairLabel(e.target.value)}
                  disabled={submitting || isPolling}
                />
                <button
                  type="submit"
                  className="primary-btn"
                  disabled={submitting || isPolling}
                >
                  {submitting ? "Uploading..." : "Upload & Assess"}
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
