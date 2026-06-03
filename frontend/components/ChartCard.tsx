import type { ReactNode } from "react";

export function ChartCard({
  title,
  description,
  children,
  actions,
  caption,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
  caption?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">{title}</h3>
          {description && <p className="mt-1 text-sm text-muted">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
      {caption && <p className="mt-3 text-xs text-muted">{caption}</p>}
    </div>
  );
}
