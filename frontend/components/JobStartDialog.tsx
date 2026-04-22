"use client";

import { useState } from "react";

interface Props {
  dimLabel: string;
  batch: number;
  fixErrors?: boolean;
  errorCount?: number;
  onConfirm: (mode: "singular" | "batch", maxSentences: number) => void;
  onCancel: () => void;
}

export default function JobStartDialog({ dimLabel, batch, fixErrors, errorCount, onConfirm, onCancel }: Props) {
  const [mode, setMode] = useState<"singular" | "batch">("singular");
  const [maxSentences, setMaxSentences] = useState(0);
  const [allSentences, setAllSentences] = useState(true);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onCancel} />
      <div className="relative bg-[#141722] border border-slate-700 rounded-xl p-5 w-96 space-y-4 shadow-2xl">
        {/* Header */}
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            {fixErrors ? "Fix Errors" : "Start Job"}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {fixErrors
              ? `${dimLabel} — ${errorCount ?? 0} errors across all batches`
              : `${dimLabel} — Batch ${batch}`}
          </p>
        </div>

        {/* Mode selection */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-400 uppercase tracking-wide">
            Processing Mode
          </label>
          <div className="space-y-1.5">
            <button
              onClick={() => setMode("singular")}
              className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${
                mode === "singular"
                  ? "bg-blue-900/40 border-blue-600 text-blue-200"
                  : "bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-600"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full border-2 flex items-center justify-center ${
                  mode === "singular" ? "border-blue-500" : "border-slate-600"
                }`}>
                  {mode === "singular" && <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />}
                </span>
                <div>
                  <span className="text-sm font-medium">Singular</span>
                  <p className="text-xs text-slate-500 mt-0.5">One sentence at a time with streaming progress</p>
                </div>
              </div>
            </button>
            <button
              onClick={() => setMode("batch")}
              className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${
                mode === "batch"
                  ? "bg-violet-900/40 border-violet-600 text-violet-200"
                  : "bg-slate-800/50 border-slate-700 text-slate-400 hover:border-slate-600"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full border-2 flex items-center justify-center ${
                  mode === "batch" ? "border-violet-500" : "border-slate-600"
                }`}>
                  {mode === "batch" && <span className="w-1.5 h-1.5 rounded-full bg-violet-500" />}
                </span>
                <div>
                  <span className="text-sm font-medium">Batch Prediction</span>
                  <p className="text-xs text-slate-500 mt-0.5">Submit to Google Cloud (faster for large volumes)</p>
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* Batch options */}
        {mode === "batch" && (
          <div className="space-y-2 pl-1">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wide">
              Sentences to process
            </label>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={allSentences}
                  onChange={(e) => {
                    setAllSentences(e.target.checked);
                    if (e.target.checked) setMaxSentences(0);
                  }}
                  className="rounded border-slate-600 bg-slate-800 text-violet-500 focus:ring-violet-500"
                />
                All remaining
              </label>
            </div>
            {!allSentences && (
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  value={maxSentences || ""}
                  onChange={(e) => setMaxSentences(parseInt(e.target.value) || 0)}
                  placeholder="Number of sentences"
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-violet-500"
                />
                <span className="text-xs text-slate-500">max</span>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <button
            onClick={onCancel}
            className="flex-1 px-3 py-2 text-sm text-slate-400 hover:text-slate-200 bg-slate-800 border border-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(mode, mode === "batch" ? (allSentences ? 0 : maxSentences) : 0)}
            className={`flex-1 px-3 py-2 text-sm text-white rounded-lg transition-colors ${
              mode === "batch"
                ? "bg-violet-700 hover:bg-violet-600"
                : "bg-blue-700 hover:bg-blue-600"
            }`}
          >
            Start
          </button>
        </div>
      </div>
    </div>
  );
}
