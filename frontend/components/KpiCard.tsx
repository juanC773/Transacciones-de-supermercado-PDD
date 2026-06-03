import { fmt } from "@/lib/format";

export function KpiCard({
  label,
  value,
  accent = "primary",
  hint,
}: {
  label: string;
  value: number;
  accent?: "primary" | "teal" | "warm";
  hint?: string;
}) {
  const bar = { primary: "bg-primary", teal: "bg-teal", warm: "bg-warm" }[accent];
  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
      <div className={`mb-3 h-1 w-10 rounded-full ${bar}`} />
      <p className="text-sm font-medium text-muted">{label}</p>
      <p className="mt-2 text-3xl font-bold tabular-nums tracking-tight">{fmt(value)}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}
