"use client";

import { useState } from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import type { DashboardData } from "@/lib/types";
import { ChartCard } from "./ChartCard";
import { TimeArea, BoxPlot, Heatmap } from "./charts";

export function AnalyticsTab({ data }: { data: DashboardData }) {
  const [serieMode, setSerieMode] = useState<"dia" | "semana">("dia");
  const [heatMode, setHeatMode] = useState<"correlacion" | "actividad">("correlacion");

  const serieData =
    serieMode === "dia"
      ? data.serie_tiempo_dia.map((d) => ({
          ...d,
          label: format(new Date(d.fecha), "d MMM", { locale: es }),
        }))
      : data.serie_tiempo_semana.map((d) => ({
          ...d,
          label: d.anio_semana.replace("2013-", ""),
        }));

  const tabBtn = (active: boolean) =>
    `rounded-md px-3 py-1.5 text-sm ${active ? "bg-primary text-white" : "bg-background text-muted hover:text-foreground"}`;

  return (
    <div className="space-y-6">
      <ChartCard
        title="Actividad transaccional"
        description="Evolución del número de transacciones"
        actions={
          <div className="flex gap-1 rounded-lg border border-border p-1">
            <button type="button" className={tabBtn(serieMode === "dia")} onClick={() => setSerieMode("dia")}>
              Día
            </button>
            <button type="button" className={tabBtn(serieMode === "semana")} onClick={() => setSerieMode("semana")}>
              Semana
            </button>
          </div>
        }
      >
        <TimeArea
          data={serieData}
          dataKey="n_transacciones"
          nameKey="label"
        />
      </ChartCard>

      <ChartCard
        title="Distribución de unidades por transacción"
        description="Valores atípicos por cliente (top 20 por volumen)"
      >
        <BoxPlot data={data.boxplot_cliente} />
      </ChartCard>

      <ChartCard
        title={heatMode === "correlacion" ? "Correlación de comportamiento (por cliente)" : "Patrón de actividad (día × mes)"}
        actions={
          <div className="flex gap-1 rounded-lg border border-border p-1">
            <button type="button" className={tabBtn(heatMode === "correlacion")} onClick={() => setHeatMode("correlacion")}>
              Correlación
            </button>
            <button type="button" className={tabBtn(heatMode === "actividad")} onClick={() => setHeatMode("actividad")}>
              Día × Mes
            </button>
          </div>
        }
      >
        {heatMode === "correlacion" ? (
          <Heatmap
            rows={data.heatmap_correlacion.labels}
            cols={data.heatmap_correlacion.labels}
            matrix={data.heatmap_correlacion.matrix}
            diverging
          />
        ) : (
          <Heatmap
            rows={data.heatmap_actividad.dias}
            cols={data.heatmap_actividad.meses}
            matrix={data.heatmap_actividad.values}
          />
        )}
      </ChartCard>
    </div>
  );
}
