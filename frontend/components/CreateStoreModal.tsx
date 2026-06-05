"use client";

import { useState } from "react";
import { crearTienda } from "@/lib/api";
import type { StoreInfo } from "@/lib/types";

export function CreateStoreModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (store: StoreInfo) => void;
}) {
  const [idInput, setIdInput] = useState("");
  const [nombre, setNombre] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  if (!open) return null;

  const reset = () => {
    setIdInput("");
    setNombre("");
    setMsg(null);
    onClose();
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = parseInt(idInput, 10);
    if (Number.isNaN(id) || id <= 0) {
      setMsg("El id debe ser un número entero positivo");
      return;
    }
    if (!nombre.trim()) {
      setMsg("Escribe un nombre para la tienda");
      return;
    }

    setSaving(true);
    setMsg(null);
    try {
      const store = await crearTienda(id, nombre.trim());
      onCreated(store);
      reset();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Error al crear tienda");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={reset}>
      <form
        className="w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-lg"
        onClick={(e) => e.stopPropagation()}
        onSubmit={onSubmit}
      >
        <h2 className="text-lg font-semibold">Crear tienda nueva</h2>
        <p className="mt-1 text-sm text-muted">
          Elige el id numérico (columna 2 del CSV) y un nombre para el dashboard. El CSV sigue el mismo formato:
          <code className="ml-1 text-xs">fecha|tienda|cliente|items</code>.
        </p>

        <label className="mt-4 block text-xs font-medium text-muted">Id de tienda</label>
        <input
          type="number"
          min={1}
          step={1}
          value={idInput}
          onChange={(e) => setIdInput(e.target.value)}
          placeholder="Ej. 111"
          className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />

        <label className="mt-3 block text-xs font-medium text-muted">Nombre</label>
        <input
          type="text"
          maxLength={80}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Ej. Sucursal Norte"
          className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />

        <p className="mt-2 text-[11px] text-muted">
          Los ítems se interpretan como SKU → categoría (igual que tiendas 103, 107 y 110). Solo la tienda 102 usa
          categorías 1–50 directas.
        </p>

        {msg && <p className="mt-3 text-sm text-red-700">{msg}</p>}

        <div className="mt-5 flex gap-2">
          <button
            type="submit"
            disabled={saving}
            className="flex-1 rounded-lg bg-primary py-2 text-sm text-white disabled:opacity-50"
          >
            {saving ? "Creando…" : "Crear tienda"}
          </button>
          <button type="button" onClick={reset} className="rounded-lg border border-border px-4 py-2 text-sm">
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
}
