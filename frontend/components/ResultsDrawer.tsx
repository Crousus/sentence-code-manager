"use client";

import { useEffect, useState } from "react";
import { fetchResults } from "@/lib/api";

interface ResultItem {
  ID: number;
  QuasiSentence: string;
  Code: number | string;
}

interface Props {
  dimId: string;
  dimLabel: string;
  onClose: () => void;
}

const CODE_BADGE: Record<string, string> = {
  "1":  "bg-red-900/50 text-red-300 border-red-700",
  "0":  "bg-slate-700 text-slate-300 border-slate-600",
  "-1": "bg-emerald-900/50 text-emerald-300 border-emerald-700",
  "99": "bg-purple-900/50 text-purple-300 border-purple-700",
  "ERROR": "bg-orange-900/50 text-orange-300 border-orange-700",
};
const CODE_LABEL: Record<string, string> = {
  "1": "Conservative", "0": "Neutral", "-1": "Liberal", "99": "Not Relevant", "ERROR": "Error",
};

export default function ResultsDrawer({ dimId, dimLabel, onClose }: Props) {
  const [results, setResults] = useState<ResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all");
  const LIMIT = 50;

  useEffect(() => {
    setLoading(true);
    fetchResults(dimId, offset, LIMIT)
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [dimId, offset]);

  const filtered = filter === "all"
    ? results
    : results.filter((r) => String(r.Code) === filter);

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/60 cursor-pointer" onClick={onClose} />
      <div className="w-full max-w-3xl bg-[#141722] border-l border-slate-700 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
          <div>
            <h2 className="font-semibold text-slate-100">{dimLabel} — Results</h2>
            <p className="text-xs text-slate-500">{total} classified sentences</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-100 text-xl leading-none">×</button>
        </div>

        {/* Filter */}
        <div className="flex gap-2 px-4 py-2 border-b border-slate-700 text-xs">
          {["all", "1", "0", "-1", "99", "ERROR"].map((v) => (
            <button
              key={v}
              onClick={() => setFilter(v)}
              className={`px-2 py-1 rounded ${filter === v ? "bg-blue-700 text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"}`}
            >
              {v === "all" ? "All" : CODE_LABEL[v] ?? v}
            </button>
          ))}
        </div>

        {/* Results list */}
        <div className="flex-1 overflow-y-auto scrollbar-thin divide-y divide-slate-800">
          {loading && <p className="p-4 text-slate-500 text-sm">Loading…</p>}
          {!loading && filtered.length === 0 && (
            <p className="p-4 text-slate-500 text-sm italic">No results.</p>
          )}
          {filtered.map((r) => {
            const code = String(r.Code);
            const badge = CODE_BADGE[code] ?? "bg-slate-700 text-slate-300 border-slate-600";
            return (
              <div key={r.ID} className="flex gap-3 px-4 py-3 hover:bg-slate-800/30">
                <span className="text-slate-500 text-xs w-10 shrink-0 pt-0.5">#{r.ID}</span>
                <p className="flex-1 text-sm text-slate-200 leading-relaxed">{r.QuasiSentence}</p>
                <span className={`shrink-0 self-start text-xs px-2 py-0.5 rounded border ${badge}`}>
                  {CODE_LABEL[code] ?? code}
                </span>
              </div>
            );
          })}
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-slate-700 text-xs text-slate-500">
          <span>{offset + 1}–{Math.min(offset + LIMIT, total)} of {total}</span>
          <div className="flex gap-2">
            <button
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - LIMIT))}
              className="px-2 py-1 bg-slate-700 rounded disabled:opacity-40 hover:bg-slate-600"
            >
              ← Prev
            </button>
            <button
              disabled={offset + LIMIT >= total}
              onClick={() => setOffset(offset + LIMIT)}
              className="px-2 py-1 bg-slate-700 rounded disabled:opacity-40 hover:bg-slate-600"
            >
              Next →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
