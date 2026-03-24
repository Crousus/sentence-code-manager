const API = "";

export interface BatchInfo {
  batch: number;
  total: number;
  processed: number;
  code_distribution: Record<string, number>;
  status: "idle" | "partial" | "running" | "completed";
  job_id: string | null;
}

export interface Dimension {
  id: string;
  label: string;
  model: string;
  status: "idle" | "partial" | "running" | "completed" | "error";
  total: number;
  processed: number;
  code_distribution: Record<string, number>;
  batches: BatchInfo[];
  refine_of?: string;
}

export interface Job {
  job_id: string;
  dimension: string;
  batch: number;
  status: "running" | "completed" | "error" | "stopped";
  started_at: string;
  finished_at: string | null;
  total: number;
  processed: number;
  log_count: number;
  logs?: string[];
}

export interface Stats {
  total_dimensions: number;
  completed_dimensions: number;
  total_sentences: number;
  total_processed: number;
  running_jobs: number;
  total_jobs_ever: number;
}

export async function fetchDimensions(): Promise<Dimension[]> {
  const res = await fetch(`${API}/api/dimensions`);
  if (!res.ok) throw new Error("Failed to fetch dimensions");
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${API}/api/stats`);
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function startJob(dimension: string, batch: number): Promise<{ job_id: string }> {
  const res = await fetch(`${API}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dimension, batch }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to start job");
  }
  return res.json();
}

export async function stopJob(jobId: string): Promise<void> {
  const res = await fetch(`${API}/api/jobs/${jobId}/stop`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to stop job");
}

export async function fetchJobLogs(
  jobId: string,
  offset = 0
): Promise<{ logs: string[]; total: number; status: string }> {
  const res = await fetch(`${API}/api/jobs/${jobId}/logs?offset=${offset}`);
  if (!res.ok) throw new Error("Failed to fetch logs");
  return res.json();
}

export async function fetchResults(
  dimId: string,
  offset = 0,
  limit = 50
): Promise<{ total: number; results: Array<{ ID: number; QuasiSentence: string; Code: number | string }> }> {
  const res = await fetch(`${API}/api/results/${dimId}?offset=${offset}&limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch results");
  return res.json();
}

export function getStreamUrl(jobId: string): string {
  // Connect directly to FastAPI for SSE — bypasses Next.js proxy buffering.
  // Uses the same hostname as the page so it works over the local network.
  const host =
    typeof window !== "undefined"
      ? `http://${window.location.hostname}:8000`
      : (process.env.BACKEND_URL ?? "http://localhost:8000");
  return `${host}/api/jobs/${jobId}/stream`;
}

export interface RuntimeConfig {
  project_id: string;
  location: string;
}

export async function fetchConfig(): Promise<RuntimeConfig> {
  const res = await fetch(`${API}/api/config`);
  if (!res.ok) throw new Error("Failed to fetch config");
  return res.json();
}

export async function updateConfig(patch: Partial<RuntimeConfig>): Promise<RuntimeConfig> {
  const res = await fetch(`${API}/api/config`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error("Failed to update config");
  return res.json();
}

// ---------------------------------------------------------------------------
// Dimension CRUD
// ---------------------------------------------------------------------------

export interface DimensionConfig {
  id: string;
  label: string;
  model: string;
  prompt_template: string;
}

export async function fetchDimensionConfig(dimId: string): Promise<DimensionConfig> {
  const res = await fetch(`${API}/api/dimensions/${dimId}/config`);
  if (!res.ok) throw new Error("Failed to fetch dimension config");
  return res.json();
}

export async function createDimension(cfg: DimensionConfig): Promise<DimensionConfig> {
  const res = await fetch(`${API}/api/dimensions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create dimension");
  }
  return res.json();
}

export interface RefineCreate {
  id: string;
  label: string;
  model: string;
  prompt_template: string;
}

export async function createRefineDimension(
  parentId: string,
  req: RefineCreate
): Promise<{ id: string; total_sentences: number; batches: number[] }> {
  const res = await fetch(`${API}/api/dimensions/${parentId}/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create refinement");
  }
  return res.json();
}

export async function updateDimension(
  dimId: string,
  patch: Partial<Omit<DimensionConfig, "id">>
): Promise<DimensionConfig> {
  const res = await fetch(`${API}/api/dimensions/${dimId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to update dimension");
  }
  return res.json();
}
