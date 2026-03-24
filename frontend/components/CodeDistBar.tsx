"use client";

interface Props {
  dist: Record<string, number>;
  total: number;
}

const CODE_COLORS: Record<string, string> = {
  "1":  "bg-red-500",
  "0":  "bg-slate-400",
  "-1": "bg-emerald-500",
  "99": "bg-purple-500",
  "ERROR": "bg-orange-500",
};

const CODE_LABELS: Record<string, string> = {
  "1":  "Conservative",
  "0":  "Neutral",
  "-1": "Liberal",
  "99": "Not Relevant",
  "ERROR": "Error",
};

export default function CodeDistBar({ dist, total }: Props) {
  const processed = Object.values(dist).reduce((a, b) => a + b, 0);
  if (processed === 0) return (
    <div className="h-2 bg-slate-700 rounded-full w-full" title="No data yet" />
  );

  const segments = Object.entries(dist).sort(([a], [b]) => {
    const order = ["1", "0", "-1", "99", "ERROR"];
    return order.indexOf(a) - order.indexOf(b);
  });

  return (
    <div className="space-y-1">
      <div className="flex h-2 rounded-full overflow-hidden w-full gap-px">
        {segments.map(([code, count]) => {
          const pct = (count / processed) * 100;
          return (
            <div
              key={code}
              className={`${CODE_COLORS[code] ?? "bg-gray-500"} transition-all`}
              style={{ width: `${pct}%` }}
              title={`${CODE_LABELS[code] ?? code}: ${count} (${pct.toFixed(1)}%)`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-slate-400">
        {segments.map(([code, count]) => (
          <span key={code} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-sm inline-block ${CODE_COLORS[code] ?? "bg-gray-500"}`} />
            {count}
          </span>
        ))}
      </div>
    </div>
  );
}
