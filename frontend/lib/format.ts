export const fmt = (n: number) =>
  new Intl.NumberFormat("es-ES").format(Math.round(n));

export const fmtCompact = (n: number) =>
  new Intl.NumberFormat("es-ES", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
