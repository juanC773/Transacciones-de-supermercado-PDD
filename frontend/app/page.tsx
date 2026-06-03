"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchDashboard, fetchMeta, fetchSegmentacion, regenerarEtl } from "@/lib/api";
import type { DashboardData, Filters, Meta, SegmentacionData } from "@/lib/types";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { ResumenTab } from "@/components/ResumenTab";
import { AnalyticsTab } from "@/components/AnalyticsTab";
import { SegmentacionTab } from "@/components/SegmentacionTab";
import { RecomendadorTab } from "@/components/RecomendadorTab";

const DEFAULT_FILTERS: Filters = {
  tiendas: [102, 103, 107, 110],
  fecha_min: "2013-01-01",
  fecha_max: "2013-06-30",
};

type TabId = "resumen" | "analytics" | "segmentacion" | "recomendaciones";

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

const TABS: { id: TabId; label: string }[] = [
  { id: "resumen", label: "Resumen Ejecutivo" },
  { id: "analytics", label: "Visualizaciones" },
  { id: "segmentacion", label: "Segmentación" },
  { id: "recomendaciones", label: "Recomendaciones" },
];

export default function HomePage() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const debouncedFilters = useDebounced(filters, 350);
  const [tab, setTab] = useState<TabId>("resumen");
  const [meta, setMeta] = useState<Meta | undefined>();
  const [data, setData] = useState<DashboardData | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [regenerando, setRegenerando] = useState(false);
  const [segData, setSegData] = useState<SegmentacionData | null>(null);
  const [segVersion, setSegVersion] = useState(0);

  useEffect(() => {
    fetchSegmentacion(DEFAULT_FILTERS)
      .then(setSegData)
      .catch(() => setSegData(null));
  }, [segVersion]);

  useEffect(() => {
    fetchMeta()
      .then(setMeta)
      .catch(() => {});
  }, []);

  const loadDashboard = useCallback(async (f: Filters) => {
    if (f.tiendas.length === 0) {
      setData(undefined);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const d = await fetchDashboard(f);
      setData(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error de conexión con la API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard(debouncedFilters);
  }, [debouncedFilters, loadDashboard]);

  const onRegenerar = async () => {
    setRegenerando(true);
    try {
      await regenerarEtl();
      const m = await fetchMeta();
      setMeta(m);
      await loadDashboard(filters);
      setSegVersion((v) => v + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al regenerar");
    } finally {
      setRegenerando(false);
    }
  };

  const tabBtn = (id: TabId) =>
    `rounded-md px-4 py-2 text-sm font-medium whitespace-nowrap ${
      tab === id ? "bg-primary text-white" : "text-muted hover:text-foreground"
    }`;

  return (
    <div className="flex min-h-screen w-full bg-background">
      <Sidebar
        filters={filters}
        setFilters={setFilters}
        meta={meta}
        onRegenerar={onRegenerar}
        regenerando={regenerando}
        onDatosActualizados={async () => {
          const m = await fetchMeta();
          setMeta(m);
          await loadDashboard(filters);
          setSegVersion((v) => v + 1);
        }}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <Header filters={filters} />

        <div className="flex-1 overflow-y-auto px-6 py-6 lg:px-8">
          {filters.tiendas.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card py-24 text-center">
              <h3 className="text-lg font-semibold">Selecciona al menos una tienda</h3>
              <p className="mt-1 text-sm text-muted">Usa el panel izquierdo para activar tiendas.</p>
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-800">
              <p className="font-semibold">No se pudo cargar el dashboard</p>
              <p className="mt-1 text-sm">{error}</p>
            </div>
          ) : (
            <>
              <div className="mb-6 flex flex-wrap gap-2 rounded-lg border border-border bg-card p-1 w-fit max-w-full">
                {TABS.map(({ id, label }) => (
                  <button key={id} type="button" className={tabBtn(id)} onClick={() => setTab(id)}>
                    {label}
                  </button>
                ))}
              </div>

              <div className={tab === "segmentacion" ? "block" : "hidden"}>
                <SegmentacionTab initialSeg={segData} segVersion={segVersion} />
              </div>

              <div className={tab === "recomendaciones" ? "block" : "hidden"}>
                <RecomendadorTab filters={filters} />
              </div>

              <div className={tab === "resumen" || tab === "analytics" ? "block" : "hidden"}>
                {loading || !data ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-4">
                      {[0, 1, 2].map((i) => (
                        <div key={i} className="h-32 animate-pulse rounded-xl bg-slate-200" />
                      ))}
                    </div>
                    <div className="h-80 animate-pulse rounded-xl bg-slate-200" />
                  </div>
                ) : tab === "resumen" ? (
                  <ResumenTab data={data} />
                ) : (
                  <AnalyticsTab data={data} />
                )}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
