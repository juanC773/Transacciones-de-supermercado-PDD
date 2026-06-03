"use client";

import { useState } from "react";
import type { Filters, Meta } from "@/lib/types";
import { fmtCompact } from "@/lib/format";
import { procesarNuevosDatos } from "@/lib/api";
import { StoreUploadModal } from "./StoreUploadModal";

const STORES = [102, 103, 107, 110];

export function Sidebar({
  filters,
  setFilters,
  meta,
  onRegenerar,
  regenerando,
  onDatosActualizados,
}: {
  filters: Filters;
  setFilters: (f: Filters) => void;
  meta?: Meta;
  onRegenerar: () => void;
  regenerando: boolean;
  onDatosActualizados?: () => void;
}) {
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [uploadStore, setUploadStore] = useState<number | null>(null);

  const toggleStore = (id: number) => {
    const has = filters.tiendas.includes(id);
    setFilters({
      ...filters,
      tiendas: has ? filters.tiendas.filter((s) => s !== id) : [...filters.tiendas, id].sort(),
    });
  };

  const onProcesar = async () => {
    setProcesando(true);
    setStatusMsg(null);
    try {
      await procesarNuevosDatos();
      setStatusMsg("Listo. Recarga o espera — el dashboard ya usa los Parquet nuevos.");
      onDatosActualizados?.();
    } catch (err) {
      setStatusMsg(err instanceof Error ? err.message : "Error al procesar");
    } finally {
      setProcesando(false);
    }
  };

  return (
    <>
      <aside className="hidden w-[280px] shrink-0 border-r border-border bg-card lg:flex lg:flex-col">
        <div className="flex items-center gap-3 border-b border-border px-6 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white">
            TS
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight">Transacciones</p>
            <p className="text-xs text-muted">Supermercado · 2013</p>
          </div>
        </div>

        <div className="flex-1 space-y-7 overflow-y-auto px-5 py-6">
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Tiendas</p>
            <p className="mb-2 text-[11px] text-muted">+ agrega transacciones al CSV de esa tienda</p>
            <div className="space-y-2">
              {STORES.map((id) => (
                <div
                  key={id}
                  className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2.5"
                >
                  <label className="flex flex-1 cursor-pointer items-center gap-3">
                    <input
                      type="checkbox"
                      checked={filters.tiendas.includes(id)}
                      onChange={() => toggleStore(id)}
                      className="h-4 w-4 rounded border-border text-primary"
                    />
                    <span className="text-sm font-medium">Tienda {id}</span>
                  </label>
                  <button
                    type="button"
                    title="Agregar datos a esta tienda"
                    onClick={() => setUploadStore(id)}
                    className="rounded-md border border-border px-2 py-1 text-xs font-medium text-primary hover:bg-primary/5"
                  >
                    +
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Rango de fechas</p>
            <div className="space-y-2">
              <div>
                <label className="mb-1 block text-xs text-muted">Desde</label>
                <input
                  type="date"
                  min="2013-01-01"
                  max="2013-06-30"
                  value={filters.fecha_min}
                  onChange={(e) => setFilters({ ...filters, fecha_min: e.target.value })}
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted">Hasta</label>
                <input
                  type="date"
                  min="2013-01-01"
                  max="2013-06-30"
                  value={filters.fecha_max}
                  onChange={(e) => setFilters({ ...filters, fecha_max: e.target.value })}
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
                />
              </div>
            </div>
            <button
              type="button"
              className="mt-2 w-full rounded-lg border border-border py-2 text-xs text-muted hover:bg-background"
              onClick={() =>
                setFilters({ tiendas: STORES, fecha_min: "2013-01-01", fecha_max: "2013-06-30" })
              }
            >
              Restablecer filtros
            </button>
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Actualizar dashboard</p>
            <button
              type="button"
              onClick={onProcesar}
              disabled={procesando || regenerando}
              className="w-full rounded-lg border border-primary py-2 text-sm text-primary disabled:opacity-60"
            >
              {procesando ? "Procesando ETL+ML…" : "Procesar nuevos datos"}
            </button>
            <p className="mt-1 text-[11px] text-muted">Después de usar + en una tienda</p>
            {statusMsg && <p className="mt-2 text-xs text-muted">{statusMsg}</p>}
          </div>

          <button
            type="button"
            onClick={onRegenerar}
            disabled={regenerando || procesando}
            className="w-full rounded-lg bg-primary py-2.5 text-sm font-medium text-white disabled:opacity-60"
          >
            {regenerando ? "Procesando ETL…" : "Regenerar datos (Spark)"}
          </button>
        </div>

        {meta && (
          <div className="space-y-1 border-t border-border px-6 py-4 text-xs text-muted">
            <p className="font-semibold text-foreground">Dataset (global)</p>
            <p>{fmtCompact(meta.total_transacciones)} transacciones</p>
            <p>{fmtCompact(meta.total_clientes)} clientes</p>
            <p>{fmtCompact(meta.total_unidades)} unidades</p>
            {meta.etl_engine && <p className="pt-1 text-[10px] uppercase">ETL: {meta.etl_engine}</p>}
          </div>
        )}
      </aside>

      {uploadStore !== null && (
        <StoreUploadModal
          storeId={uploadStore}
          open
          onClose={() => setUploadStore(null)}
          onAgregado={(n) => setStatusMsg(`${n} líneas en tienda ${uploadStore}. Pulsa «Procesar nuevos datos».`)}
        />
      )}
    </>
  );
}
