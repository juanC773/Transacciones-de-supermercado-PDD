export type BoxPlotStat = {
  name: string;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
};

export type Filters = {
  tiendas: number[];
  fecha_min: string;
  fecha_max: string;
};

export type DashboardData = {
  kpis: { total_ventas: number; total_transacciones: number; total_clientes: number };
  top_categorias: { id_categoria: number; nombre_categoria: string; unidades: number }[];
  top_clientes: { id_cliente: number; n_transacciones: number }[];
  actividad_dia_semana: { dia: string; n_transacciones: number }[];
  categorias_volumen: { nombre_categoria: string; unidades: number }[];
  serie_tiempo_dia: { fecha: string; n_transacciones: number }[];
  serie_tiempo_semana: { anio_semana: string; n_transacciones: number }[];
  boxplot_cliente: BoxPlotStat[];
  heatmap_correlacion: { labels: string[]; matrix: number[][] };
  heatmap_actividad: { dias: string[]; meses: string[]; values: number[][] };
};

export type Meta = {
  fecha_min: string;
  fecha_max: string;
  tiendas: number[];
  total_transacciones: number;
  total_clientes: number;
  total_unidades: number;
  etl_engine?: string;
};

export type ClusterProfile = {
  cluster_id: number;
  nombre: string;
  n_clientes: number;
  pct_clientes: number;
  n_transacciones_prom: number;
  unidades_prom: number;
  n_categorias_prom: number;
  frecuencia_semanal_prom: number;
  descripcion: string;
};

export type SegmentacionData = {
  meta: { n_clusters: number; n_clientes: number; profiles: ClusterProfile[] };
  scatter: { id_cliente: number; pc1: number; pc2: number; cluster_id: number }[];
};

export type RecomendacionCategoria = {
  id_categoria: number;
  nombre_categoria: string;
  score: number;
  motivo: string;
  confidence?: number;
};
