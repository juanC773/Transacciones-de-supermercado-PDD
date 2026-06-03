import type { DashboardData, Filters, Meta, RecomendacionCategoria, SegmentacionData } from "./types";
import { formatUploadError } from "./validateTranCsv";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function filterParams(filters: Filters) {
  return new URLSearchParams({
    tiendas: filters.tiendas.join(","),
    fecha_min: filters.fecha_min,
    fecha_max: filters.fecha_max,
  });
}

export async function fetchMeta(): Promise<Meta> {
  const res = await fetch(`${API_URL}/api/meta`, { cache: "no-store" });
  if (!res.ok) throw new Error("No se pudo cargar metadata");
  return res.json();
}

export async function fetchDashboard(filters: Filters): Promise<DashboardData> {
  const res = await fetch(`${API_URL}/api/dashboard?${filterParams(filters)}`, { cache: "no-store" });
  if (!res.ok) throw new Error("No se pudo cargar el dashboard");
  return res.json();
}

export async function regenerarEtl(): Promise<void> {
  const res = await fetch(`${API_URL}/api/etl/regenerar`, { method: "POST" });
  if (!res.ok) throw new Error("Error al regenerar ETL");
}

export async function fetchSegmentacion(filters: Filters): Promise<SegmentacionData> {
  const res = await fetch(`${API_URL}/api/segmentacion?${filterParams(filters)}`, { cache: "no-store" });
  if (!res.ok) throw new Error("No se pudo cargar segmentación");
  return res.json();
}

export async function fetchRecomendacionesCliente(
  idCliente: number,
  filters: Filters,
): Promise<{ recomendaciones: RecomendacionCategoria[] }> {
  const p = filterParams(filters);
  p.set("id_cliente", String(idCliente));
  const res = await fetch(`${API_URL}/api/recomendaciones/cliente?${p}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Sin recomendaciones para este cliente");
  return res.json();
}

export async function fetchRecomendacionesCategoria(
  idCategoria: number,
): Promise<{ recomendaciones: RecomendacionCategoria[] }> {
  const res = await fetch(
    `${API_URL}/api/recomendaciones/categoria?id_categoria=${idCategoria}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error("Sin reglas para esta categoría");
  return res.json();
}

export async function agregarDatosTienda(
  idTienda: number,
  file: File,
): Promise<{ ok: boolean; lineas_agregadas: number; mensaje: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/ingest/tienda/${idTienda}`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(formatUploadError((err as { detail?: unknown }).detail));
  }
  return res.json();
}

export async function procesarNuevosDatos(): Promise<void> {
  const res = await fetch(`${API_URL}/api/ingest/procesar`, { method: "POST" });
  if (!res.ok) throw new Error("Error al procesar nuevos datos");
}
