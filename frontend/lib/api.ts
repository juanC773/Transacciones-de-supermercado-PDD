import type { DashboardData, Filters, Meta, RecomendacionCategoria, SegmentacionData, StoreInfo } from "./types";
import { formatUploadError } from "./validateTranCsv";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ETL_TIMEOUT_MS = 280_000;
const DATAPROC_POLL_MS = 5_000;
const DATAPROC_MAX_POLLS = 120;

type EtlRunResponse = {
  ok?: boolean;
  async?: boolean;
  job_id?: string;
  engine?: string;
  state?: string;
  mensaje?: string;
};

async function pollDataprocJob(jobId: string): Promise<void> {
  for (let i = 0; i < DATAPROC_MAX_POLLS; i++) {
    await new Promise((r) => setTimeout(r, DATAPROC_POLL_MS));
    const res = await fetch(`${API_URL}/api/etl/job/${encodeURIComponent(jobId)}`, { cache: "no-store" });
    if (!res.ok) throw new Error("No se pudo consultar el job de Dataproc");
    const data = (await res.json()) as { state?: string; ok?: boolean; detail?: string };
    if (data.state === "DONE" && data.ok) return;
    if (data.state === "ERROR" || data.state === "CANCELLED") {
      throw new Error(data.detail ?? `Job Dataproc terminó en estado ${data.state}`);
    }
  }
  throw new Error("El ETL en Dataproc tardó demasiado. Revisa el cluster y vuelve a intentar.");
}

async function waitForEtlResult(res: Response): Promise<EtlRunResponse> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = (err as { detail?: string }).detail;
    throw new Error(typeof detail === "string" ? detail : "Error en el ETL");
  }
  const data = (await res.json()) as EtlRunResponse;
  if (data.async && data.job_id) {
    await pollDataprocJob(data.job_id);
  }
  return data;
}

async function fetchLong(url: string, init?: RequestInit): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ETL_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

function filterParams(filters: Filters) {
  return new URLSearchParams({
    tiendas: filters.tiendas.join(","),
    fecha_min: filters.fecha_min,
    fecha_max: filters.fecha_max,
  });
}

export async function fetchTiendas(): Promise<StoreInfo[]> {
  const res = await fetch(`${API_URL}/api/tiendas`, { cache: "no-store" });
  if (!res.ok) throw new Error("No se pudo cargar la lista de tiendas");
  const data = (await res.json()) as { tiendas: StoreInfo[] };
  return data.tiendas;
}

export async function crearTienda(idTienda: number, nombre: string): Promise<StoreInfo> {
  const res = await fetch(`${API_URL}/api/tiendas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_tienda: idTienda, nombre }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = (err as { detail?: string }).detail;
    throw new Error(typeof detail === "string" ? detail : "No se pudo crear la tienda");
  }
  const data = (await res.json()) as { tienda: StoreInfo };
  return data.tienda;
}

export async function eliminarTienda(idTienda: number): Promise<{ mensaje: string }> {
  const res = await fetchLong(`${API_URL}/api/tiendas/${idTienda}`, { method: "DELETE" });
  const data = (await waitForEtlResult(res)) as EtlRunResponse & { mensaje?: string };
  return { mensaje: data.mensaje ?? "Tienda eliminada." };
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
  const res = await fetchLong(`${API_URL}/api/etl/regenerar`, { method: "POST" });
  await waitForEtlResult(res);
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
  const res = await fetchLong(`${API_URL}/api/ingest/procesar`, { method: "POST" });
  await waitForEtlResult(res);
}
