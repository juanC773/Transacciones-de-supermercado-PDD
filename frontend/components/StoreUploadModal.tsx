"use client";

import { useRef, useState } from "react";
import { agregarDatosTienda } from "@/lib/api";
import { validateTranCsvFileForStore, type TranCsvValidation } from "@/lib/validateTranCsv";

function ValidationResult({ check, storeId }: { check: TranCsvValidation; storeId: number }) {
  const pct =
    check.lineas_totales > 0
      ? Math.round((check.lineas_validas / check.lineas_totales) * 100)
      : 0;

  return (
    <div
      className={`mt-3 rounded-lg border p-3 text-sm ${
        check.ok ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"
      }`}
    >
      <p className={`font-medium ${check.ok ? "text-green-800" : "text-red-800"}`}>
        {check.ok ? "Validación correcta" : "Validación rechazada"}
      </p>
      <p className={`mt-1 text-xs ${check.ok ? "text-green-700" : "text-red-700"}`}>
        {check.lineas_validas} de {check.lineas_totales} líneas válidas ({pct}%) — columna tienda debe ser{" "}
        <strong>{storeId}</strong>
      </p>
      {check.ok ? (
        <p className="mt-2 text-xs text-green-700">
          Puedes agregar al CSV. Luego usa «Procesar nuevos datos» en el sidebar.
        </p>
      ) : (
        <div className="mt-2 text-red-800">
          <p className="text-xs font-medium">Errores detectados:</p>
          <ul className="mt-1 max-h-40 list-inside list-disc overflow-y-auto text-xs">
            {check.errores.map((e, i) => (
              <li key={`${i}-${e}`}>{e}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function StoreUploadModal({
  store,
  open,
  onClose,
  onAgregado,
}: {
  store: { id: number; nombre: string };
  open: boolean;
  onClose: () => void;
  onAgregado?: (info: { lineasAgregadas: number; lineasValidas: number; lineasTotales: number }) => void;
}) {
  const storeId = store.id;
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [check, setCheck] = useState<TranCsvValidation | null>(null);
  const [checking, setChecking] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [msgIsError, setMsgIsError] = useState(false);

  if (!open) return null;

  const onPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    setFile(f ?? null);
    setMsg(null);
    setMsgIsError(false);
    setCheck(null);
    if (!f) return;
    setChecking(true);
    try {
      setCheck(await validateTranCsvFileForStore(f, storeId));
    } finally {
      setChecking(false);
    }
    e.target.value = "";
  };

  const onAgregar = async () => {
    if (!file || !check?.ok) return;
    setUploading(true);
    setMsg(null);
    setMsgIsError(false);
    try {
      const r = await agregarDatosTienda(storeId, file);
      onAgregado?.({
        lineasAgregadas: r.lineas_agregadas,
        lineasValidas: check.lineas_validas,
        lineasTotales: check.lineas_totales,
      });
      reset();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Error");
      setMsgIsError(true);
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setCheck(null);
    setMsg(null);
    setMsgIsError(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={reset}>
      <div
        className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-xl border border-border bg-card p-5 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold">Agregar datos — {store.nombre}</h2>
        <p className="mt-1 text-sm text-muted">
          Las filas se <strong>añaden</strong> al CSV de esta tienda. Columna 2 (tienda) debe ser el id{" "}
          <code className="rounded bg-background px-1 text-xs">{storeId}</code> en todas las filas.
        </p>
        <p className="mt-2 text-[11px] text-muted">
          Misma validación para tiendas del curso y nuevas: al elegir el archivo (aquí) y al guardar (API).
          Ejemplos en <code className="text-[10px]">DataSet/ejemplos-prueba/</code>.
        </p>

        <input ref={inputRef} type="file" accept=".csv" className="hidden" onChange={onPick} />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-4 w-full rounded-lg border border-border py-2 text-sm hover:bg-background"
        >
          Elegir CSV
        </button>

        {file && <p className="mt-2 text-xs text-muted">Archivo: {file.name}</p>}

        {checking && <p className="mt-3 text-sm text-muted">Revisando formato y columna tienda…</p>}

        {check && !checking && <ValidationResult check={check} storeId={storeId} />}

        {msg && (
          <p
            className={`mt-3 whitespace-pre-wrap text-sm ${msgIsError ? "text-red-700" : "text-muted"}`}
            role={msgIsError ? "alert" : undefined}
          >
            {msg}
          </p>
        )}

        <div className="mt-5 flex gap-2">
          <button
            type="button"
            disabled={!check?.ok || uploading}
            onClick={onAgregar}
            className="flex-1 rounded-lg bg-primary py-2 text-sm text-white disabled:opacity-50"
          >
            {uploading ? "Guardando…" : "Agregar al CSV"}
          </button>
          <button type="button" onClick={reset} className="rounded-lg border border-border px-4 py-2 text-sm">
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
