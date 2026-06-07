"use client";

import { useCallback, useEffect, useState } from "react";
import type { Filters, Meta, StoreInfo } from "@/lib/types";
import { fmtCompact } from "@/lib/format";
import { eliminarTienda, fetchTiendas, procesarNuevosDatos } from "@/lib/api";
import { StoreUploadModal } from "./StoreUploadModal";
import { CreateStoreModal } from "./CreateStoreModal";

const DEFAULT_STORE_IDS = [102, 103, 107, 110];

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
  const [stores, setStores] = useState<StoreInfo[]>([]);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [statusOk, setStatusOk] = useState(false);
  const [procesando, setProcesando] = useState(false);
  const [uploadStore, setUploadStore] = useState<StoreInfo | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadStores = useCallback(async () => {
    try {
      setStores(await fetchTiendas());
    } catch {
      setStores(DEFAULT_STORE_IDS.map((id) => ({ id, nombre: `Tienda ${id}`, es_base: true })));
    }
  }, []);

  useEffect(() => {
    loadStores();
  }, [loadStores]);

  const toggleStore = (id: number) => {
    const has = filters.tiendas.includes(id);
    setFilters({
      ...filters,
      tiendas: has ? filters.tiendas.filter((s) => s !== id) : [...filters.tiendas, id].sort((a, b) => a - b),
    });
  };

  const onProcesar = async () => {
    setProcesando(true);
    setStatusMsg(null);
    setStatusOk(false);
    try {
      await procesarNuevosDatos();
      setStatusOk(true);
      setStatusMsg("Listo. El dashboard ya usa los Parquet nuevos.");
      onDatosActualizados?.();
    } catch (err) {
      setStatusOk(false);
      setStatusMsg(err instanceof Error ? err.message : "Error al procesar");
    } finally {
      setProcesando(false);
    }
  };

  const onStoreCreated = async (store: StoreInfo) => {
    await loadStores();
    setFilters({
      ...filters,
      tiendas: [...filters.tiendas, store.id].sort((a, b) => a - b),
    });
    setStatusOk(true);
    setStatusMsg(`Tienda ${store.id} creada. Usa + para cargar su CSV.`);
  };

  const onDeleteStore = async (store: StoreInfo) => {
    if (
      !window.confirm(
        `¿Eliminar «${store.nombre}» (id ${store.id})? Se borra el registro y ${store.id}_Tran.csv.`,
      )
    ) {
      return;
    }
    setDeletingId(store.id);
    setStatusMsg(null);
    try {
      await eliminarTienda(store.id);
      if (uploadStore?.id === store.id) setUploadStore(null);
      await loadStores();
      setFilters({ ...filters, tiendas: filters.tiendas.filter((t) => t !== store.id) });
      setStatusOk(true);
      setStatusMsg(`Tienda ${store.id} eliminada.`);
    } catch (err) {
      setStatusOk(false);
      setStatusMsg(err instanceof Error ? err.message : "Error al eliminar");
    } finally {
      setDeletingId(null);
    }
  };

  const resetFilters = async () => {
    const list = await fetchTiendas().catch(() => stores);
    setStores(list);
    const ids = list.length > 0 ? list.map((s) => s.id) : DEFAULT_STORE_IDS;
    setFilters({ tiendas: ids, fecha_min: "2013-01-01", fecha_max: "2013-06-30" });
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
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">Tiendas</p>
              <button
                type="button"
                onClick={() => setCreateOpen(true)}
                className="rounded-md border border-border px-2 py-0.5 text-[11px] font-medium text-primary hover:bg-primary/5"
              >
                + Nueva
              </button>
            </div>
            <p className="mb-2 text-[11px] text-muted">
              + sube CSV · × elimina tiendas creadas por ti
            </p>
            <div className="space-y-2">
              {stores.map((store) => (
                <div
                  key={store.id}
                  className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2.5"
                >
                  <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-3">
                    <input
                      type="checkbox"
                      checked={filters.tiendas.includes(store.id)}
                      onChange={() => toggleStore(store.id)}
                      className="h-4 w-4 shrink-0 rounded border-border text-primary"
                    />
                    <span className="truncate text-sm font-medium" title={store.nombre}>
                      {store.nombre}
                      <span className="ml-1 text-xs text-muted">({store.id})</span>
                    </span>
                  </label>
                  <div className="flex shrink-0 gap-1">
                    <button
                      type="button"
                      title="Agregar datos a esta tienda"
                      onClick={() => setUploadStore(store)}
                      className="rounded-md border border-border px-2 py-1 text-xs font-medium text-primary hover:bg-primary/5"
                    >
                      +
                    </button>
                    {!store.es_base && (
                      <button
                        type="button"
                        title="Eliminar tienda"
                        disabled={deletingId === store.id}
                        onClick={() => onDeleteStore(store)}
                        className="rounded-md border border-border px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        ×
                      </button>
                    )}
                  </div>
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
              onClick={resetFilters}
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
            {statusMsg && (
              <p className={`mt-2 text-xs ${statusOk ? "font-medium text-green-700" : "text-muted"}`}>
                {statusMsg}
              </p>
            )}
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
          store={uploadStore}
          open
          onClose={() => setUploadStore(null)}
          onAgregado={({ lineasAgregadas, lineasValidas, lineasTotales }) => {
            setStatusOk(true);
            setStatusMsg(
              `CSV OK: ${lineasAgregadas} líneas agregadas a ${uploadStore.nombre} (${lineasValidas}/${lineasTotales} validadas). Pulsa «Procesar nuevos datos».`,
            );
          }}
        />
      )}

      <CreateStoreModal open={createOpen} onClose={() => setCreateOpen(false)} onCreated={onStoreCreated} />
    </>
  );
}
