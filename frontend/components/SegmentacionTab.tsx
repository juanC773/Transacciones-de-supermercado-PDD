"use client";

import { useEffect, useState } from "react";
import type { SegmentacionData } from "@/lib/types";
import { fetchSegmentacion } from "@/lib/api";
import { ChartCard } from "./ChartCard";
import { ClusterScatter } from "./charts";

type Props = {
  initialSeg?: SegmentacionData | null;
  segVersion?: number;
};

export function SegmentacionTab({ initialSeg, segVersion = 0 }: Props) {
  const [seg, setSeg] = useState<SegmentacionData | null>(initialSeg ?? null);
  const [loading, setLoading] = useState(!initialSeg);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialSeg) {
      setSeg(initialSeg);
      setLoading(false);
      return;
    }
    setLoading(true);
    fetchSegmentacion({ tiendas: [102, 103, 107, 110], fecha_min: "2013-01-01", fecha_max: "2013-06-30" })
      .then(setSeg)
      .catch((e) => {
        setSeg(null);
        setError(e instanceof Error ? e.message : "No se pudo cargar segmentación");
      })
      .finally(() => setLoading(false));
  }, [initialSeg, segVersion]);

  if (loading) {
    return <div className="h-96 animate-pulse rounded-xl bg-slate-200" />;
  }

  if (!seg) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
        <p className="font-semibold">Segmentación no disponible</p>
        <p className="mt-1 text-sm">
          {error ?? "Pulsa Regenerar datos en el panel izquierdo (ETL + K-Means)."}
        </p>
      </div>
    );
  }

  return (
    <ChartCard
      title="Segmentación de clientes (K-Means)"
      description="Variables: frecuencia, volumen, diversidad de categorías y frecuencia semanal. Vista PCA 2D."
    >
      <ClusterScatter points={seg.scatter} />
      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {seg.meta.profiles.map((p) => (
          <div key={p.cluster_id} className="rounded-lg border border-border bg-background p-4">
            <p className="font-semibold text-primary">
              Cluster {p.cluster_id}: {p.nombre}
            </p>
            <p className="mt-1 text-xs text-muted">{p.descripcion}</p>
            <ul className="mt-2 space-y-0.5 text-xs tabular-nums text-muted">
              <li>{p.n_clientes.toLocaleString()} clientes ({p.pct_clientes}%)</li>
              <li>Prom. {p.n_transacciones_prom} tx · {p.unidades_prom} unidades</li>
              <li>{p.n_categorias_prom} categorías · frec. {p.frecuencia_semanal_prom}/sem</li>
            </ul>
          </div>
        ))}
      </div>
    </ChartCard>
  );
}
