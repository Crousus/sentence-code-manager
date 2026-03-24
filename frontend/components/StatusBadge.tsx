"use client";

type Status = "idle" | "partial" | "running" | "completed" | "error" | "stopped";

const CONFIG: Record<Status, { label: string; classes: string; dot?: string }> = {
  idle:      { label: "Idle",       classes: "bg-slate-700 text-slate-300" },
  partial:   { label: "Partial",    classes: "bg-amber-900/60 text-amber-300" },
  running:   { label: "Running",    classes: "bg-blue-900/60 text-blue-300", dot: "animate-pulse bg-blue-400" },
  completed: { label: "Completed",  classes: "bg-emerald-900/60 text-emerald-300" },
  error:     { label: "Error",      classes: "bg-red-900/60 text-red-300" },
  stopped:   { label: "Stopped",    classes: "bg-orange-900/60 text-orange-300" },
};

export default function StatusBadge({ status }: { status: Status }) {
  const cfg = CONFIG[status] ?? CONFIG.idle;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.classes}`}>
      {cfg.dot && <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />}
      {cfg.label}
    </span>
  );
}
