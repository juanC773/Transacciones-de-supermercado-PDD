export const BASE_STORES = [102, 103, 107, 110] as const;

export type TranCsvValidation = {
  ok: boolean;
  errores: string[];
  advertencias: string[];
  lineas_validas: number;
  lineas_totales: number;
  tienda: number | null;
};

const CATEGORY_STORES = new Set([102]);

function validateLine(line: string, lineNo: number, expectedStore: number): string[] {
  const errs: string[] = [];
  const raw = line.trim();
  if (!raw) return [`Línea ${lineNo}: vacía`];
  if (raw.toLowerCase().startsWith("fecha|") || raw.toLowerCase().includes("tienda|cliente")) {
    return [`Línea ${lineNo}: parece encabezado; el CSV no debe tener header`];
  }

  const parts = line.split("|");
  if (parts.length < 4) {
    return [`Línea ${lineNo}: formato incorrecto (se esperan 4 campos separados por |)`];
  }
  if (parts.length > 4) {
    errs.push(`Línea ${lineNo}: demasiados campos | (${parts.length})`);
  }

  const [fechaS, tiendaS, clienteS, prodS] = parts.map((p) => p.trim());
  if (!/^\d{4}-\d{2}-\d{2}$/.test(fechaS) || Number.isNaN(Date.parse(fechaS))) {
    errs.push(`Línea ${lineNo}: fecha inválida '${fechaS}'`);
  }

  const tienda = parseInt(tiendaS, 10);
  if (Number.isNaN(tienda)) errs.push(`Línea ${lineNo}: tienda debe ser numérica`);
  else if (tienda !== expectedStore) {
    errs.push(`Línea ${lineNo}: tienda ${tienda} debe ser ${expectedStore}`);
  }

  const cliente = parseInt(clienteS, 10);
  if (Number.isNaN(cliente)) errs.push(`Línea ${lineNo}: cliente debe ser numérico`);
  else if (cliente <= 0) errs.push(`Línea ${lineNo}: cliente debe ser > 0`);

  const tokens = prodS.split(/\s+/).filter(Boolean);
  if (tokens.length === 0) {
    errs.push(`Línea ${lineNo}: faltan productos/categorías`);
  } else {
    for (const tok of tokens) {
      if (!/^\d+$/.test(tok)) {
        errs.push(`Línea ${lineNo}: ítem no numérico '${tok}'`);
        break;
      }
    }
    if (CATEGORY_STORES.has(expectedStore)) {
      for (const tok of tokens) {
        const v = parseInt(tok, 10);
        if (v < 1 || v > 50) {
          errs.push(`Línea ${lineNo}: categoría ${v} fuera de 1-50`);
          break;
        }
      }
    }
  }
  return errs;
}

export function validateTranCsvForStore(content: string, storeId: number): TranCsvValidation {
  const nonEmpty = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n").filter((l) => l.trim());
  if (nonEmpty.length === 0) {
    return {
      ok: false,
      errores: ["Archivo vacío"],
      advertencias: [],
      lineas_validas: 0,
      lineas_totales: 0,
      tienda: storeId,
    };
  }

  const errores: string[] = [];
  let valid = 0;
  for (let i = 0; i < nonEmpty.length; i++) {
    const lineErrs = validateLine(nonEmpty[i], i + 1, storeId);
    if (lineErrs.length) errores.push(...lineErrs);
    else valid += 1;
    if (errores.length >= 12) {
      errores.push("…");
      break;
    }
  }

  const ratio = valid / nonEmpty.length;
  if (ratio < 0.95) {
    errores.unshift(`Solo ${valid}/${nonEmpty.length} líneas válidas (mínimo 95%)`);
  }

  return {
    ok: errores.length === 0 && valid > 0,
    errores,
    advertencias: [],
    lineas_validas: valid,
    lineas_totales: nonEmpty.length,
    tienda: storeId,
  };
}

export async function validateTranCsvFileForStore(file: File, storeId: number): Promise<TranCsvValidation> {
  if (!file.name.toLowerCase().endsWith(".csv")) {
    return {
      ok: false,
      errores: ["Debe ser un archivo .csv"],
      advertencias: [],
      lineas_validas: 0,
      lineas_totales: 0,
      tienda: storeId,
    };
  }
  return validateTranCsvForStore(await file.text(), storeId);
}

export function formatUploadError(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const d = detail as { mensaje?: string; errores?: string[] };
    if (d.errores?.length) {
      return [d.mensaje ?? "Validación fallida", ...d.errores.slice(0, 8)].join("\n");
    }
    if (d.mensaje) return d.mensaje;
  }
  return "Error al subir archivo";
}
