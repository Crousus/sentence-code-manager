"use client";

import { useCallback, useEffect, useState } from "react";
import { useMemo } from "react";
import {
  fetchDimensions,
  fetchDimensionConfig,
  fetchStats,
  startJob,
  stopJob,
  type BatchInfo,
  type Dimension,
  type Stats,
} from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import CodeDistBar from "@/components/CodeDistBar";
import LogDrawer from "@/components/LogDrawer";
import ResultsDrawer from "@/components/ResultsDrawer";
import ConfigPanel from "@/components/ConfigPanel";
import DimensionFormDrawer, { type FormTarget } from "@/components/DimensionFormDrawer";

function pct(a: number, b: number) {
  if (b === 0) return 0;
  return Math.min(100, Math.round((a / b) * 100));
}

function modelColor(model: string) {
  if (model.includes("3-flash")) return "text-violet-400";
  if (model.includes("2.5")) return "text-cyan-400";
  return "text-slate-400";
}

const BATCH_STATUS_COLORS: Record<string, string> = {
  completed: "bg-emerald-500",
  running: "bg-blue-500 animate-pulse",
  partial: "bg-amber-500",
  idle: "bg-slate-700",
};

export default function Dashboard() {
  const [dimensions, setDimensions] = useState<Dimension[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "running" | "completed" | "idle" | "partial">("all");
  const [actionPending, setActionPending] = useState<Set<string>>(new Set());
  const [logTarget, setLogTarget] = useState<{ jobId: string; label: string } | null>(null);
  const [resultsTarget, setResultsTarget] = useState<{ dimId: string; label: string } | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [formTarget, setFormTarget] = useState<FormTarget | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [dims, st] = await Promise.all([fetchDimensions(), fetchStats()]);
      setDimensions(dims);
      setStats(st);
      setError(null);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [refresh]);

  const handleStart = async (dim: Dimension, batch: number) => {
    const key = `${dim.id}:${batch}`;
    setActionPending((p) => new Set(p).add(key));
    try {
      const res = await startJob(dim.id, batch);
      setLogTarget({ jobId: res.job_id, label: `${dim.label} — Batch ${batch}` });
      await refresh();
    } catch (e: unknown) {
      alert(String(e));
    } finally {
      setActionPending((p) => { const n = new Set(p); n.delete(key); return n; });
    }
  };

  const handleRefine = async (dim: Dimension) => {
    try {
      const cfg = await fetchDimensionConfig(dim.id);
      setFormTarget({
        mode: "refine",
        parentId: dim.id,
        parentLabel: dim.label,
        prefill: {
          label: cfg.label + " (Refined)",
          model: cfg.model,
          prompt_template: cfg.prompt_template,
        },
      });
    } catch (e: unknown) {
      alert(String(e));
    }
  };

  const handleDuplicate = async (dim: Dimension) => {
    try {
      const cfg = await fetchDimensionConfig(dim.id);
      setFormTarget({ mode: "create", prefill: { label: cfg.label, model: cfg.model, prompt_template: cfg.prompt_template } });
    } catch (e: unknown) {
      alert(String(e));
    }
  };

  const handleStop = async (dim: Dimension, batch: BatchInfo) => {
    if (!batch.job_id) return;
    const key = `${dim.id}:${batch.batch}`;
    setActionPending((p) => new Set(p).add(key));
    try {
      await stopJob(batch.job_id);
      await refresh();
    } catch (e: unknown) {
      alert(String(e));
    } finally {
      setActionPending((p) => { const n = new Set(p); n.delete(key); return n; });
    }
  };

  // Sort: each base dimension followed immediately by its refinements.
  // Then apply the status filter (refines inherit their slot after the parent).
  const sortedDims = useMemo(() => {
    const bases = dimensions.filter((d) => !d.refine_of);
    const refines = dimensions.filter((d) => d.refine_of);
    const ordered: Dimension[] = [];
    for (const base of bases) {
      ordered.push(base);
      ordered.push(...refines.filter((r) => r.refine_of === base.id));
    }
    // Orphan refinements (parent not present)
    for (const r of refines) {
      if (!ordered.includes(r)) ordered.push(r);
    }
    return ordered;
  }, [dimensions]);

  const filteredDims = sortedDims.filter((d) =>
    filter === "all" ? true : d.status === filter
  );

  const FILTER_TABS = [
    { key: "all", label: "All" },
    { key: "running", label: "Running" },
    { key: "partial", label: "Partial" },
    { key: "completed", label: "Completed" },
    { key: "idle", label: "Idle" },
  ] as const;

  return (
    <div className="min-h-screen bg-[#0f1117]">
      {/* Header */}
      <header className="border-b border-slate-800 bg-[#141722] sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex-1">
            <h1 className="text-lg font-bold text-slate-100 leading-tight">
              Manifesto Classifier
            </h1>
            <p className="text-xs text-slate-500">Political manifesto classification system</p>
          </div>

          {stats && (
            <div className="flex gap-6 text-sm">
              <StatPill label="Dimensions" value={`${stats.completed_dimensions}/${stats.total_dimensions}`} />
              <StatPill
                label="Sentences"
                value={`${stats.total_processed.toLocaleString()}/${stats.total_sentences.toLocaleString()}`}
              />
              <StatPill
                label="Active jobs"
                value={String(stats.running_jobs)}
                highlight={stats.running_jobs > 0}
              />
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={() => setFormTarget({ mode: "create" })}
              className="px-2.5 py-1 rounded-md text-xs bg-blue-800 text-blue-200 border border-blue-700 hover:bg-blue-700 hover:text-white transition-colors"
              title="Add a new classification dimension"
            >
              + Dimension
            </button>
            <button
              onClick={() => setShowConfig(true)}
              className="px-2.5 py-1 rounded-md text-xs bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700 hover:text-slate-200 transition-colors"
              title="Vertex AI configuration"
            >
              ⚙ Config
            </button>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <span
                className={`w-2 h-2 rounded-full ${
                  error ? "bg-red-500" : "bg-emerald-500 animate-pulse"
                }`}
              />
              {error ? "Disconnected" : "Live"}
            </div>
          </div>
        </div>

        {stats && stats.total_sentences > 0 && (
          <div className="h-1 bg-slate-800">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-violet-600 transition-all duration-500"
              style={{ width: `${pct(stats.total_processed, stats.total_sentences)}%` }}
            />
          </div>
        )}
      </header>

      {/* Filter tabs */}
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-2 flex-wrap">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
              filter === tab.key
                ? "bg-blue-700 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
            }`}
          >
            {tab.label}
            {tab.key !== "all" && (
              <span className="ml-1.5 text-xs opacity-70">
                {dimensions.filter((d) => d.status === tab.key).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Grid */}
      <main className="max-w-7xl mx-auto px-4 pb-12">
        {loading && (
          <div className="flex items-center justify-center py-24 text-slate-500">
            <span className="mr-2">⟳</span> Connecting to backend…
          </div>
        )}

        {error && !loading && (
          <div className="rounded-xl border border-red-800 bg-red-950/30 p-6 text-center text-sm text-red-300 mt-4">
            <p className="font-medium mb-1">Cannot reach backend</p>
            <p className="text-red-400 font-mono text-xs">{error}</p>
            <p className="mt-2 text-slate-400 text-xs">
              Make sure the FastAPI server is running on{" "}
              <code className="bg-slate-800 px-1 rounded">localhost:8000</code>
            </p>
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDims.map((dim) => (
              <DimensionCard
                key={dim.id}
                dim={dim}
                actionPending={actionPending}
                onStart={(batch) => handleStart(dim, batch)}
                onStop={(batch) => handleStop(dim, batch)}
                onViewLogs={(jobId) => setLogTarget({ jobId, label: dim.label })}
                onViewResults={() => setResultsTarget({ dimId: dim.id, label: dim.label })}
                onEdit={() => setFormTarget({ mode: "edit", dimId: dim.id })}
                onDuplicate={() => handleDuplicate(dim)}
                onRefine={() => handleRefine(dim)}
              />
            ))}
          </div>
        )}
      </main>

      {logTarget && (
        <LogDrawer
          jobId={logTarget.jobId}
          dimLabel={logTarget.label}
          onClose={() => setLogTarget(null)}
        />
      )}
      {resultsTarget && (
        <ResultsDrawer
          dimId={resultsTarget.dimId}
          dimLabel={resultsTarget.label}
          onClose={() => setResultsTarget(null)}
        />
      )}
      {showConfig && <ConfigPanel onClose={() => setShowConfig(false)} />}
      {formTarget && (
        <DimensionFormDrawer
          target={formTarget}
          onClose={() => setFormTarget(null)}
          onSaved={refresh}
        />
      )}
    </div>
  );
}

function StatPill({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="text-center">
      <div className={`font-semibold ${highlight ? "text-blue-400" : "text-slate-200"}`}>
        {value}
      </div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

interface CardProps {
  dim: Dimension;
  actionPending: Set<string>;
  onStart: (batch: number) => void;
  onStop: (batch: BatchInfo) => void;
  onViewLogs: (jobId: string) => void;
  onViewResults: () => void;
  onEdit: () => void;
  onDuplicate: () => void;
  onRefine: () => void;
}

function DimensionCard({ dim, actionPending, onStart, onStop, onViewLogs, onViewResults, onEdit, onDuplicate, onRefine }: CardProps) {
  const progress = pct(dim.processed, dim.total);
  const isRunning = dim.status === "running";
  const hasResults = dim.processed > 0;
  const isRefine = !!dim.refine_of;

  return (
    <div
      className={`rounded-xl border flex flex-col transition-all ${
        isRefine
          ? isRunning
            ? "bg-[#17131f] border-violet-600/70 shadow-lg shadow-violet-950/50"
            : "bg-[#17131f] border-violet-800/50 hover:border-violet-700/70"
          : isRunning
          ? "bg-[#141722] border-blue-700/60 shadow-lg shadow-blue-950/50"
          : "bg-[#141722] border-slate-800 hover:border-slate-700"
      }`}
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-slate-800">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="font-semibold text-slate-100 text-sm leading-tight">{dim.label}</h3>
            {isRefine && (
              <p className="text-xs text-violet-400 mt-0.5">
                ↺ refinement of <span className="font-mono">{dim.refine_of}</span>
              </p>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {!isRefine && (
              <button
                onClick={onRefine}
                title="Create refinement"
                className="text-slate-400 hover:text-violet-300 text-base px-1.5 transition-colors"
              >
                ↺
              </button>
            )}
            <button
              onClick={onDuplicate}
              title="Duplicate dimension"
              className="text-slate-400 hover:text-slate-100 text-base px-1.5 transition-colors"
            >
              ⎘
            </button>
            <button
              onClick={onEdit}
              title="Edit dimension"
              className="text-slate-400 hover:text-slate-100 text-base px-1.5 transition-colors"
            >
              ✎
            </button>
            <StatusBadge status={dim.status as "idle" | "running" | "completed" | "partial" | "error"} />
          </div>
        </div>
        <div className="mt-1.5 text-xs text-slate-500">
          <span className={`font-mono ${modelColor(dim.model)}`}>{dim.model}</span>
        </div>
      </div>

      {/* Overall progress */}
      <div className="px-4 py-3 border-b border-slate-800 space-y-2">
        <div className="flex justify-between text-xs text-slate-400">
          <span>
            {dim.processed.toLocaleString()} / {dim.total.toLocaleString()} total
          </span>
          <span className="font-medium text-slate-300">{progress}%</span>
        </div>

        <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isRunning
                ? "bg-blue-500"
                : progress === 100
                ? "bg-emerald-500"
                : "bg-slate-500"
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>

        {hasResults && (
          <CodeDistBar dist={dim.code_distribution} total={dim.total} />
        )}
      </div>

      {/* Batch sub-cells */}
      <div className="px-4 py-3 border-b border-slate-800">
        <p className="text-xs text-slate-500 mb-2">Batches</p>
        <div className="flex flex-wrap gap-1.5">
          {dim.batches.map((b) => (
            <BatchCell
              key={b.batch}
              batch={b}
              dimId={dim.id}
              pending={actionPending.has(`${dim.id}:${b.batch}`)}
              onStart={() => onStart(b.batch)}
              onStop={() => onStop(b)}
              onViewLogs={() => b.job_id && onViewLogs(b.job_id)}
            />
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 py-3 flex gap-2 flex-wrap">
        {dim.batches
          .filter((b) => b.status === "running")
          .map((b) => (
            <button
              key={b.batch}
              disabled={actionPending.has(`${dim.id}:${b.batch}`)}
              onClick={() => onStop(b)}
              className="px-3 py-1.5 text-xs bg-red-900/40 text-red-300 border border-red-800/60 rounded-lg hover:bg-red-900/60 disabled:opacity-50 transition-colors"
            >
              {actionPending.has(`${dim.id}:${b.batch}`) ? "Stopping…" : `■ Stop B${b.batch}`}
            </button>
          ))}
        {hasResults && (
          <button
            onClick={onViewResults}
            className="flex-1 px-3 py-1.5 text-xs bg-slate-800 text-slate-400 border border-slate-700 rounded-lg hover:bg-slate-700 transition-colors"
          >
            Results
          </button>
        )}
      </div>
    </div>
  );
}

function BatchCell({
  batch,
  dimId,
  pending,
  onStart,
  onStop,
  onViewLogs,
}: {
  batch: BatchInfo;
  dimId: string;
  pending: boolean;
  onStart: () => void;
  onStop: () => void;
  onViewLogs: () => void;
}) {
  const p = pct(batch.processed, batch.total);
  const color = BATCH_STATUS_COLORS[batch.status] ?? "bg-slate-700";

  return (
    <div className="flex flex-col items-center gap-1 group relative">
      {/* Dot indicator */}
      <button
        onClick={
          batch.status === "running"
            ? onStop
            : batch.status === "completed"
            ? undefined
            : onStart
        }
        disabled={pending || batch.status === "completed"}
        title={
          batch.status === "running"
            ? `Batch ${batch.batch}: running (${batch.processed}/${batch.total}) — click to stop`
            : batch.status === "completed"
            ? `Batch ${batch.batch}: done (${batch.processed}/${batch.total})`
            : batch.status === "partial"
            ? `Batch ${batch.batch}: partial (${batch.processed}/${batch.total}) — click to resume`
            : `Batch ${batch.batch}: idle (${batch.total} sentences) — click to start`
        }
        className={`w-7 h-7 rounded-md flex items-center justify-center text-[10px] font-bold transition-all
          ${color}
          ${batch.status !== "completed" && !pending ? "hover:brightness-125 cursor-pointer" : ""}
          ${pending ? "opacity-50 cursor-wait" : ""}
          ${batch.status === "completed" ? "cursor-default" : ""}
        `}
      >
        {pending ? "…" : batch.batch}
      </button>

      {/* Mini progress bar */}
      {batch.total > 0 && (
        <div className="w-full h-0.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full ${color.replace("animate-pulse", "")} transition-all`}
            style={{ width: `${p}%` }}
          />
        </div>
      )}

      {/* Log link for running batches */}
      {batch.status === "running" && batch.job_id && (
        <button
          onClick={onViewLogs}
          className="text-[9px] text-blue-400 hover:text-blue-300 leading-none"
        >
          logs
        </button>
      )}
    </div>
  );
}
