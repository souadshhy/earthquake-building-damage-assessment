import { AssessmentResult, JobStatus } from "../types/assessment";

export interface HealthResponse {
  status: string;
  inference_ready: boolean;
  inference_reason?: string | null;
}

export interface PreparedPair {
  pair_id: string;
  label?: string;
  width?: number;
  height?: number;
  crs?: string;
  provenance?: string;
}

export interface RejectedPair {
  pair_id: string;
  reason: string;
}

export interface PairsListResponse {
  pairs: PreparedPair[];
  rejected?: RejectedPair[];
}

export interface JobStatusResponse {
  job_id: string;
  pair_id: string;
  status: JobStatus;
  created_at?: string;
  updated_at?: string;
  model_version?: string | null;
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

export function resolveApiAssetUrl(assetUrl?: string | null): string | null {
  if (!assetUrl) return null;
  if (/^https?:\/\//i.test(assetUrl)) return assetUrl;
  const normalizedPath = assetUrl.startsWith("/") ? assetUrl : `/${assetUrl}`;
  if (
    API_BASE &&
    (normalizedPath === API_BASE || normalizedPath.startsWith(`${API_BASE}/`))
  ) {
    return normalizedPath;
  }
  return `${API_BASE}${normalizedPath}`;
}

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
        detail = body.detail.map((d: { msg?: string }) => d.msg).join("; ");
      } else if (typeof body?.error === "string") {
        detail = body.error;
      }
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

export async function fetchPreparedPairs(): Promise<PairsListResponse> {
  const res = await fetch(`${API_BASE}/pairs`);
  const data = await handleJson<PairsListResponse | PreparedPair[]>(res);
  if (Array.isArray(data)) {
    return { pairs: data, rejected: [] };
  }
  return {
    pairs: Array.isArray(data.pairs) ? data.pairs : [],
    rejected: Array.isArray(data.rejected) ? data.rejected : [],
  };
}

export async function submitPreparedPairJob(
  pairId: string
): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input_type: "prepared", pair_id: pairId }),
  });
  return handleJson<JobStatusResponse>(res);
}

export async function submitUploadJob(params: {
  beforeFile: File;
  afterFile: File;
}): Promise<JobStatusResponse> {
  const form = new FormData();
  form.append("input_type", "upload");
  form.append("before", params.beforeFile);
  form.append("after", params.afterFile);

  const res = await fetch(`${API_BASE}/jobs`, {
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
    `${API_BASE}/jobs/${encodeURIComponent(jobId)}/buildings`
  );
  return handleJson<AssessmentResult>(res);
}

export function getExportUrl(jobId: string, format: "geojson" | "csv"): string {
  return `${API_BASE}/jobs/${encodeURIComponent(jobId)}/exports/${format}`;
}
