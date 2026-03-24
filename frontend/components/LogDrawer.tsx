"use client";

import { useEffect, useRef, useState } from "react";
import { fetchJobLogs, getStreamUrl } from "@/lib/api";

interface Props {
  jobId: string | null;
  dimLabel: string;
  onClose: () => void;
}

export default function LogDrawer({ jobId, dimLabel, onClose }: Props) {
  const [logs, setLogs] = useState<string[]>([]);
  const [done, setDone] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;
    setLogs([]);
    setDone(false);

    const es = new EventSource(getStreamUrl(jobId));
    esRef.current = es;

    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.done) {
        setDone(true);
        es.close();
      } else if (data.line) {
        setLogs((prev) => [...prev, data.line]);
      }
    };

    es.onerror = () => {
      setDone(true);
      es.close();
    };

    return () => {
      es.close();
    };
  }, [jobId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const lineClass = (line: string) => {
    if (line.startsWith("SUCCESS")) return "text-emerald-400";
    if (line.startsWith("FAILED") || line.startsWith("ERROR")) return "text-red-400";
    if (line.startsWith("RETRY")) return "text-amber-400";
    if (line.startsWith("COMPLETE")) return "text-blue-400 font-bold";
    if (line.startsWith("PROCESSING")) return "text-slate-300";
    if (line.startsWith("TOTAL") || line.startsWith("RESUME") || line.startsWith("PROGRESS")) return "text-purple-400";
    return "text-slate-400";
  };

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="flex-1 bg-black/60 cursor-pointer" onClick={onClose} />

      {/* Drawer */}
      <div className="w-full max-w-2xl bg-[#141722] border-l border-slate-700 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
          <div>
            <h2 className="font-semibold text-slate-100">{dimLabel} — Logs</h2>
            <p className="text-xs text-slate-500">{jobId ?? "No job"}</p>
          </div>
          <div className="flex items-center gap-2">
            {!done && jobId && (
              <span className="flex items-center gap-1 text-xs text-blue-400">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                Live
              </span>
            )}
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-100 text-xl leading-none"
            >
              ×
            </button>
          </div>
        </div>

        {/* Log output */}
        <div className="flex-1 overflow-y-auto font-mono text-xs p-4 scrollbar-thin space-y-0.5">
          {logs.length === 0 && !done && (
            <p className="text-slate-500 italic">Waiting for output…</p>
          )}
          {logs.map((line, i) => (
            <div key={i} className={lineClass(line)}>
              {line}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {done && (
          <div className="px-4 py-2 border-t border-slate-700 text-xs text-slate-500">
            Stream ended • {logs.length} lines
          </div>
        )}
      </div>
    </div>
  );
}
