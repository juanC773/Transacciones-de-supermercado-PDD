"use client";

import { useCallback, useState } from "react";
import type { Filters, RecomendacionCategoria } from "@/lib/types";
import { fetchRecomendacionesCategoria, fetchRecomendacionesCliente } from "@/lib/api";
import { ChartCard } from "./ChartCard";
import { HorizontalBars } from "./charts";

export function RecomendadorTab({ filters }: { filters: Filters }) {
  const [clienteId, setClienteId] = useState("272914");
  const [catId, setCatId] = useState("5");
  const [recCli, setRecCli] = useState<RecomendacionCategoria[]>([]);
  const [recCat, setRecCat] = useState<RecomendacionCategoria[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingCli, setLoadingCli] = useState(false);
  const [loadingCat, setLoadingCat] = useState(false);
  const [searchedCli, setSearchedCli] = useState(false);
  const [searchedCat, setSearchedCat] = useState(false);

  const buscarCliente = useCallback(async () => {
    setError(null);
    const id = parseInt(clienteId, 10);
    if (Number.isNaN(id)) {
      setError("ID de cliente inválido");
      return;
    }
    setLoadingCli(true);
    setSearchedCli(true);
    try {
      const r = await fetchRecomendacionesCliente(id, filters);
      setRecCli(r.recomendaciones);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
      setRecCli([]);
    } finally {
      setLoadingCli(false);
    }
  }, [clienteId, filters]);

  const buscarCategoria = useCallback(async () => {
    setError(null);
    const id = parseInt(catId, 10);
    if (Number.isNaN(id) || id < 1 || id > 50) {
      setError("La categoría debe estar entre 1 y 50");
      return;
    }
    setLoadingCat(true);
    setSearchedCat(true);
    try {
      const r = await fetchRecomendacionesCategoria(id);
      setRecCat(r.recomendaciones);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
      setRecCat([]);
    } finally {
      setLoadingCat(false);
    }
  }, [catId]);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border bg-slate-50/80 p-4 text-sm text-muted">
        <p className="font-medium text-foreground">¿Cómo funciona?</p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          <li>
            <strong>Por cliente:</strong> mira qué categorías compró en el rango de fechas y tiendas del
            sidebar, busca reglas del tipo “si compró A, también suele comprar B” y sugiere categorías que
            aún no tiene.
          </li>
          <li>
            <strong>Por categoría:</strong> dado un id 1–50 (ej. 5 = panes), lista otras categorías que
            aparecen a menudo en la misma canasta.
          </li>
        </ul>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <ChartCard title="Por cliente" description="Categorías complementarias según historial de compra">
          <div className="mb-4 flex gap-2">
            <input
              type="number"
              value={clienteId}
              onChange={(e) => setClienteId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && buscarCliente()}
              placeholder="ID cliente"
              className="flex-1 rounded-lg border border-border px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={buscarCliente}
              disabled={loadingCli}
              className="rounded-lg bg-primary px-4 py-2 text-sm text-white disabled:opacity-60"
            >
              {loadingCli ? "Buscando…" : "Buscar"}
            </button>
          </div>
          {loadingCli ? (
            <p className="text-sm text-muted">Consultando historial y reglas…</p>
          ) : recCli.length > 0 ? (
            <HorizontalBars
              data={recCli.map((r) => ({ label: r.nombre_categoria, score: r.score }))}
              dataKey="score"
              nameKey="label"
              color="#7C3AED"
              height={280}
            />
          ) : searchedCli ? (
            <p className="text-sm text-amber-700">
              Sin recomendaciones para el cliente {clienteId} con los filtros actuales. Prueba otro ID del
              top 10 en Resumen Ejecutivo o amplía fechas/tiendas.
            </p>
          ) : (
            <p className="text-sm text-muted">
              Ej. un ID del top 10 clientes en Resumen Ejecutivo (como 272914).
            </p>
          )}
        </ChartCard>

        <ChartCard title="Por categoría" description="Categorías que suelen comprarse juntas">
          <div className="mb-4 flex gap-2">
            <input
              type="number"
              min={1}
              max={50}
              value={catId}
              onChange={(e) => setCatId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && buscarCategoria()}
              placeholder="ID categoría 1-50"
              className="flex-1 rounded-lg border border-border px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={buscarCategoria}
              disabled={loadingCat}
              className="rounded-lg bg-primary px-4 py-2 text-sm text-white disabled:opacity-60"
            >
              {loadingCat ? "Buscando…" : "Buscar"}
            </button>
          </div>
          {loadingCat ? (
            <p className="text-sm text-muted">Cargando reglas de asociación…</p>
          ) : recCat.length > 0 ? (
            <HorizontalBars
              data={recCat.map((r) => ({ label: r.nombre_categoria, score: r.score }))}
              dataKey="score"
              nameKey="label"
              color="#0F766E"
              height={280}
            />
          ) : searchedCat ? (
            <p className="text-sm text-amber-700">
              Sin reglas para la categoría {catId}. Prueba 5 (panes), 10 (leche) o 3 (verduras).
            </p>
          ) : (
            <p className="text-sm text-muted">Ej. categoría 5 (panes) o 10 (leche).</p>
          )}
        </ChartCard>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
