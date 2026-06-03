"use client";

import { useRef, useState } from "react";
import { agregarDatosTienda } from "@/lib/api";
import { validateTranCsvFileForStore, type TranCsvValidation } from "@/lib/validateTranCsv";

export function StoreUploadModal({
  storeId,
  open,
  onClose,
  onAgregado,
}: {
  storeId: number;
  open: boolean;
  onClose: () => void;
  onAgregado?: (lineas: number) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [check, setCheck] = useState<TranCsvValidation | null>(null);
  const [checking, setChecking] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  if (!open) return null;

  const onPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    setFile(f ?? null);
    setMsg(null);
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
    try {
      const r = await agregarDatosTienda(storeId, file);
      setMsg(r.mensaje);
      onAgregado?.(r.lineas_agregadas);
      setFile(null);
      setCheck(null);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Error");
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setCheck(null);
    setMsg(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={reset}>
      <div
        className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-xl border border-border bg-card p-5 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold">Agregar datos — Tienda {storeId}</h2>
        <p className="mt-1 text-sm text-muted">
          Las filas se <strong>añaden</strong> al CSV de esta tienda. Columna tienda debe ser{" "}
          <code className="text-xs">{storeId}</code>. Luego pulsa <strong>Procesar nuevos datos</strong> en el
          sidebar.
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

        {checking && <p className="mt-3 text-sm text-muted">Revisando formato…</p>}

        {check && !checking && (
          <div className="mt-3 rounded-lg border border-border bg-background p-3 text-sm">
            {check.ok ? (
              <p className="text-green-700">
                OK — {check.lineas_validas} líneas válidas para tienda {storeId}.
              </p>
            ) : (
              <div className="text-red-700">
                <p className="font-medium">Errores en el archivo:</p>
                <ul className="mt-1 list-inside list-disc text-xs">
                  {check.errores.slice(0, 8).map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {msg && <p className="mt-3 text-sm text-muted">{msg}</p>}

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
