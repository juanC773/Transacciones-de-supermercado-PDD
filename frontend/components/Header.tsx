"use client";

import { format } from "date-fns";
import { es } from "date-fns/locale";
import type { Filters } from "@/lib/types";

export function Header({ filters }: { filters: Filters }) {
  return (
    <header className="border-b border-border bg-card/80 px-8 py-5 backdrop-blur">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-muted">Dashboard / Análisis</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">Análisis de Transacciones</h1>
          <p className="mt-1 text-sm text-muted">
            Métricas por categoría (el dataset no incluye SKU de producto ni precios)
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-border bg-background px-3 py-1 text-xs font-medium">
            {filters.tiendas.length === 0
              ? "Sin tiendas"
              : `${filters.tiendas.length} tienda${filters.tiendas.length === 1 ? "" : "s"}: ${filters.tiendas.join(", ")}`}
          </span>
          <span className="rounded-full border border-border bg-background px-3 py-1 text-xs font-medium">
            {format(new Date(filters.fecha_min), "d MMM", { locale: es })} –{" "}
            {format(new Date(filters.fecha_max), "d MMM yyyy", { locale: es })}
          </span>
        </div>
      </div>
    </header>
  );
}
