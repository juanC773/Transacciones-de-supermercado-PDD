"use client";

import type { DashboardData } from "@/lib/types";
import { KpiCard } from "./KpiCard";
import { ChartCard } from "./ChartCard";
import { HorizontalBars, VerticalBars, Donut } from "./charts";

export function ResumenTab({ data }: { data: DashboardData }) {
  const topClientes = data.top_clientes.map((c) => ({
    ...c,
    label: `Cliente ${c.id_cliente}`,
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <KpiCard label="Unidades vendidas" value={data.kpis.total_ventas} accent="primary" hint="Suma de cantidades por categoría" />
        <KpiCard label="Transacciones" value={data.kpis.total_transacciones} accent="warm" hint="Tickets registrados" />
        <KpiCard label="Clientes únicos" value={data.kpis.total_clientes} accent="teal" hint="Compradores distintos" />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <ChartCard title="Top 10 categorías por volumen" description="Categorías con más unidades vendidas (no hay ID de producto en el dataset)">
          <HorizontalBars data={data.top_categorias} dataKey="unidades" nameKey="nombre_categoria" />
        </ChartCard>
        <ChartCard title="Top 10 clientes por actividad" description="Mayor número de transacciones">
          <HorizontalBars data={topClientes} dataKey="n_transacciones" nameKey="label" color="#0F766E" />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <ChartCard
          title="Transacciones por día de la semana"
          description="Flujo total por Lunes–Domingo en el periodo filtrado (útil para personal y promociones)"
        >
          <VerticalBars data={data.actividad_dia_semana} dataKey="n_transacciones" nameKey="dia" />
        </ChartCard>
        <ChartCard
          title="Participación del top 10 categorías"
          description="Porcentaje de unidades que concentran las 10 categorías más vendidas."
        >
          <Donut data={data.categorias_volumen} />
        </ChartCard>
      </div>
    </div>
  );
}
