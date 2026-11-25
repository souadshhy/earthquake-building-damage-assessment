import { AssessmentResult, JobStatus } from "../types/assessment";

export interface HealthResponse {
  status: string;
  inference_ready: boolean;
}

export interface PreparedPair {
  pair_id: string;
  label: string;
  region?: string;
  event_date?: string;
}

export interface JobStatusResponse {
  job_id: string;
  pair_id: string;
  status: JobStatus;
  progress?: number | null;
  error?: string | null;
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (typeof body?.error === "string") detail = body.error;
    } catch {
      // keep HTTP status fallback
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  return handleJson<HealthResponse>(res);
}

export async function fetchPreparedPairs(): Promise<PreparedPair[]> {
  const res = await fetch(`${API_BASE}/pairs`);
  return handleJson<PreparedPair[]>(res);
}

export async function submitPreparedPairJob(
  pairId: string
): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pair_id: pairId }),
  });
  return handleJson<JobStatusResponse>(res);
}

export async function submitUploadJob(params: {
  beforeFile: File;
  afterFile: File;
  pairLabel?: string;
}): Promise<JobStatusResponse> {
  const form = new FormData();
  form.append("before_image", params.beforeFile);
  form.append("after_image", params.afterFile);
  if (params.pairLabel?.trim()) {
    form.append("pair_id", params.pairLabel.trim());
  }

  const res = await fetch(`${API_BASE}/jobs/upload`, {
    method: "POST",
    body: form,
  });
  return handleJson<JobStatusResponse>(res);
}

export async function fetchJobStatus(
  jobId: string
): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}`);
  return handleJson<JobStatusResponse>(res);
}

export async function fetchJobResult(
  jobId: string
): Promise<AssessmentResult> {
  const res = await fetch(
    `${API_BASE}/jobs/${encodeURIComponent(jobId)}/result`
  );
  return handleJson<AssessmentResult>(res);
}

export function getExportUrl(jobId: string, format: "geojson" | "csv"): string {
  return `${API_BASE}/jobs/${encodeURIComponent(jobId)}/export.${format}`;
}
