"use client";

import { useEffect, useState } from "react";
import {
  createDimension,
  createRefineDimension,
  fetchDimensionConfig,
  updateDimension,
  type DimensionConfig,
} from "@/lib/api";

const KNOWN_MODELS = ["gemini-2.5-flash", "gemini-3-flash-preview"];

interface CreateTarget {
  mode: "create";
  prefill?: Partial<DimensionConfig>;
}

interface EditTarget {
  mode: "edit";
  dimId: string;
}

interface RefineTarget {
  mode: "refine";
  parentId: string;
  parentLabel: string;
  prefill: Pick<DimensionConfig, "label" | "model" | "prompt_template">;
}

export type FormTarget = CreateTarget | EditTarget | RefineTarget;

interface Props {
  target: FormTarget;
  onClose: () => void;
  onSaved: () => void;
}

export default function DimensionFormDrawer({ target, onClose, onSaved }: Props) {
  const [id, setId] = useState(() => {
    if (target.mode === "create") return target.prefill?.id ?? "";
    if (target.mode === "refine") return target.parentId + "_r";
    return target.dimId;
  });
  const [label, setLabel] = useState(() => {
    if (target.mode === "create") return target.prefill?.label ?? "";
    if (target.mode === "refine") return target.prefill.label;
    return "";
  });
  const [model, setModel] = useState(() => {
    if (target.mode === "create") return target.prefill?.model ?? KNOWN_MODELS[0];
    if (target.mode === "refine") return target.prefill.model;
    return KNOWN_MODELS[0];
  });
  const [prompt, setPrompt] = useState(() => {
    if (target.mode === "create") return target.prefill?.prompt_template ?? "";
    if (target.mode === "refine") return target.prefill.prompt_template;
    return "";
  });
  const [loading, setLoading] = useState(target.mode === "edit");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (target.mode !== "edit") return;
    fetchDimensionConfig(target.dimId)
      .then((cfg) => {
        setLabel(cfg.label);
        setModel(cfg.model);
        setPrompt(cfg.prompt_template);
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });
  }, [target.mode, target.mode === "edit" ? target.dimId : ""]);

  const handleSave = async () => {
    setError(null);
    setSaving(true);
    try {
      if (target.mode === "create") {
        if (!id.trim()) throw new Error("ID is required");
        if (!/^[a-z][a-z0-9_]*$/.test(id))
          throw new Error("ID must start with a letter and contain only lowercase letters, digits, or underscores");
        if (!label.trim()) throw new Error("Label is required");
        await createDimension({ id, label, model, prompt_template: prompt });
      } else if (target.mode === "refine") {
        if (!id.trim()) throw new Error("ID is required");
        if (!/^[a-z][a-z0-9_]*$/.test(id))
          throw new Error("ID must start with a letter and contain only lowercase letters, digits, or underscores");
        if (!label.trim()) throw new Error("Label is required");
        await createRefineDimension(target.parentId, { id, label, model, prompt_template: prompt });
      } else {
        if (!label.trim()) throw new Error("Label is required");
        await updateDimension(target.dimId, { label, model, prompt_template: prompt });
      }
      onSaved();
      onClose();
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const isEdit = target.mode === "edit";
  const isRefine = target.mode === "refine";
  const title = isEdit
    ? "Edit dimension"
    : isRefine
    ? `Refine: ${target.parentLabel}`
    : target.prefill
    ? "New dimension (duplicate)"
    : "New dimension";

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="flex-1 bg-black/60 cursor-pointer" onClick={onClose} />

      {/* Drawer */}
      <div className="w-full max-w-2xl bg-[#141722] border-l border-slate-700 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 shrink-0">
          <div>
            <h2 className="font-semibold text-slate-100">{title}</h2>
            {isEdit && (
              <p className="text-xs text-slate-500 mt-0.5">
                Changes apply to new jobs only — running jobs are not affected.
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 text-xl leading-none ml-4"
          >
            ×
          </button>
        </div>

        {/* Body */}
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
            Loading…
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Refine info banner */}
            {isRefine && (
              <div className="rounded-lg bg-violet-950/40 border border-violet-700/50 px-3 py-2.5 text-xs text-violet-300 space-y-1">
                <p className="font-semibold text-violet-200">Refinement input</p>
                <p>
                  Sentences coded <code className="bg-violet-900/50 px-1 rounded">99</code> (not relevant) will be
                  excluded from <span className="text-violet-200 font-medium">{target.parentLabel}</span> results.
                  Batches are created automatically — one per 7 000 sentences, equally distributed.
                </p>
              </div>
            )}

            {/* ID — create / refine only */}
            {!isEdit && (
              <FormField
                label="ID (slug)"
                hint="Lowercase letters, digits, underscores. Cannot be changed later."
              >
                <input
                  value={id}
                  onChange={(e) =>
                    setId(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))
                  }
                  placeholder="e.g. womens_rights"
                  className={INPUT}
                  spellCheck={false}
                />
              </FormField>
            )}

            {/* Label */}
            <FormField label="Label">
              <input
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="Display name shown in the dashboard"
                className={INPUT}
              />
            </FormField>

            {/* Model */}
            <FormField label="Model">
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className={INPUT}
              >
                {KNOWN_MODELS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
                {!KNOWN_MODELS.includes(model) && (
                  <option value={model}>{model}</option>
                )}
              </select>
            </FormField>

            {/* Prompt template */}
            <FormField
              label="Prompt template"
              hint="Use {ID} and {sentence} as placeholders for the sentence being classified."
            >
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={26}
                spellCheck={false}
                className={`${INPUT} font-mono text-xs resize-y`}
              />
            </FormField>

            {error && (
              <p className="text-sm text-red-400 bg-red-950/40 border border-red-800/60 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="px-4 py-3 border-t border-slate-700 flex items-center justify-end gap-2 shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || loading}
            className="px-4 py-2 text-sm bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-white rounded-lg transition-colors"
          >
            {saving ? "Saving…" : isEdit ? "Save changes" : isRefine ? "Create refinement" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

const INPUT =
  "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500";

function FormField({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-slate-400 uppercase tracking-wide">
        {label}
      </label>
      {hint && <p className="text-xs text-slate-600">{hint}</p>}
      {children}
    </div>
  );
}
