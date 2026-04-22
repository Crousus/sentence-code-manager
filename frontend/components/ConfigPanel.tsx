"use client";

import { useEffect, useState } from "react";
import { fetchConfig, updateConfig, type RuntimeConfig } from "@/lib/api";

// model is per-dimension (configured in backend/config.py)

const KNOWN_PROJECTS: string[] = [];

const KNOWN_LOCATIONS = ["global", "us-central1", "europe-west1"];

interface Props {
  onClose: () => void;
}

export default function ConfigPanel({ onClose }: Props) {
  const [cfg, setCfg] = useState<RuntimeConfig | null>(null);
  const [draft, setDraft] = useState<RuntimeConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchConfig().then((c) => { setCfg(c); setDraft(c); });
  }, []);

  const handleSave = async () => {
    if (!draft) return;
    setSaving(true);
    try {
      const updated = await updateConfig(draft);
      setCfg(updated);
      setDraft(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      alert(String(e));
    } finally {
      setSaving(false);
    }
  };

  const dirty = cfg && draft && (
    draft.project_id !== cfg.project_id ||
    draft.location !== cfg.location ||
    draft.gcs_bucket !== cfg.gcs_bucket
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end">
      <div className="flex-1 bg-black/40 cursor-pointer h-full" onClick={onClose} />
      <div className="w-full max-w-sm bg-[#141722] border-l border-slate-700 h-full flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
          <h2 className="font-semibold text-slate-100 text-sm">Vertex AI Configuration</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-100 text-xl leading-none">×</button>
        </div>

        {!draft ? (
          <p className="p-4 text-slate-500 text-sm">Loading…</p>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            <p className="text-xs text-slate-500">
              These settings apply to all new classification jobs. Running jobs are not affected.
            </p>

            <Field label="GCP Project ID">
              <select
                value={draft.project_id}
                onChange={(e) => setDraft({ ...draft, project_id: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
              >
                {KNOWN_PROJECTS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <input
                value={draft.project_id}
                onChange={(e) => setDraft({ ...draft, project_id: e.target.value })}
                placeholder="or type a custom project ID"
                className="mt-1.5 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
            </Field>

            <Field label="Location">
              <select
                value={draft.location}
                onChange={(e) => setDraft({ ...draft, location: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
              >
                {KNOWN_LOCATIONS.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </Field>

            <Field label="GCS Bucket">
              <input
                value={draft.gcs_bucket}
                onChange={(e) => setDraft({ ...draft, gcs_bucket: e.target.value })}
                placeholder="my-project-batch-staging"
                className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
              <p className="text-xs text-slate-600 mt-1">Required for batch prediction mode. Bucket name only, no gs:// prefix.</p>
            </Field>

            <div className="pt-2 flex gap-2">
              <button
                onClick={handleSave}
                disabled={saving || !dirty}
                className="flex-1 px-3 py-2 text-sm bg-blue-700 text-white rounded-lg hover:bg-blue-600 disabled:opacity-40 transition-colors"
              >
                {saving ? "Saving…" : saved ? "Saved ✓" : "Apply"}
              </button>
              <button
                onClick={() => setDraft(cfg)}
                disabled={!dirty}
                className="px-3 py-2 text-sm bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 disabled:opacity-40 transition-colors"
              >
                Reset
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-slate-400 uppercase tracking-wide">{label}</label>
      {children}
    </div>
  );
}
