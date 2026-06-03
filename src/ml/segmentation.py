"""
Segmentación de clientes con K-Means.
Variables: frecuencia, volumen, diversidad de categorías, frecuencia semanal.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ML_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "ml"
FEATURE_COLS = ["n_transacciones", "unidades", "n_categorias", "frecuencia_semanal"]
N_CLUSTERS = 4
SCATTER_SAMPLE = 800  # puntos en el gráfico (menos = render más rápido)


def _cluster_labels(centroids: np.ndarray) -> list[str]:
    """Etiquetas legibles según el centroide de cada cluster."""
    labels = []
    med = np.median(centroids, axis=0)
    for c in centroids:
        freq, vol, div, fsem = c
        if freq >= med[0] and vol >= med[1]:
            labels.append("Clientes intensivos")
        elif fsem >= med[3]:
            labels.append("Visitas frecuentes, canasta moderada")
        elif div >= med[2]:
            labels.append("Alta diversidad de categorías")
        else:
            labels.append("Compradores ocasionales")
    return labels


def train_segmentation(por_cliente: pd.DataFrame) -> dict:
    ML_DIR.mkdir(parents=True, exist_ok=True)
    df = por_cliente.dropna(subset=FEATURE_COLS).copy()
    if len(df) < N_CLUSTERS * 10:
        raise ValueError("Muy pocos clientes para segmentar")

    X = df[FEATURE_COLS].astype(float).values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    df["cluster_id"] = km.fit_predict(Xs)

    pca = PCA(n_components=2, random_state=42)
    xy = pca.fit_transform(Xs)
    df["pc1"] = xy[:, 0]
    df["pc2"] = xy[:, 1]

    centroids_raw = scaler.inverse_transform(km.cluster_centers_)
    names = _cluster_labels(centroids_raw)

    profiles = []
    for cid in range(N_CLUSTERS):
        sub = df[df["cluster_id"] == cid]
        profiles.append(
            {
                "cluster_id": int(cid),
                "nombre": names[cid],
                "n_clientes": int(len(sub)),
                "pct_clientes": round(100 * len(sub) / len(df), 1),
                "n_transacciones_prom": round(float(sub["n_transacciones"].mean()), 1),
                "unidades_prom": round(float(sub["unidades"].mean()), 1),
                "n_categorias_prom": round(float(sub["n_categorias"].mean()), 1),
                "frecuencia_semanal_prom": round(float(sub["frecuencia_semanal"].mean()), 2),
                "descripcion": (
                    f"Grupo con ~{len(sub):,} clientes: "
                    f"promedio {sub['n_transacciones'].mean():.0f} transacciones, "
                    f"{sub['unidades'].mean():.0f} unidades y "
                    f"{sub['n_categorias'].mean():.0f} categorías distintas."
                ),
            }
        )

    out_cols = ["id_tienda", "id_cliente", "cluster_id", "pc1", "pc2"] + FEATURE_COLS
    df[out_cols].to_parquet(ML_DIR / "segmentacion_clientes.parquet", index=False)
    joblib.dump({"scaler": scaler, "kmeans": km, "pca": pca}, ML_DIR / "segmentacion_model.joblib")

    scatter_df = df if len(df) <= SCATTER_SAMPLE else df.sample(SCATTER_SAMPLE, random_state=42)
    scatter = scatter_df[["id_cliente", "pc1", "pc2", "cluster_id"]].to_dict(orient="records")
    (ML_DIR / "segmentacion_scatter.json").write_text(json.dumps(scatter), encoding="utf-8")

    meta = {
        "n_clusters": N_CLUSTERS,
        "n_clientes": int(len(df)),
        "feature_cols": FEATURE_COLS,
        "profiles": profiles,
    }
    (ML_DIR / "segmentacion_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def load_segmentation_meta() -> dict | None:
    path = ML_DIR / "segmentacion_meta.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_segmentation_scatter() -> list[dict]:
    """Lee scatter pre-guardado en JSON (rápido); fallback Parquet solo si falta."""
    json_path = ML_DIR / "segmentacion_scatter.json"
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    path = ML_DIR / "segmentacion_clientes.parquet"
    if not path.exists():
        return []
    df = pd.read_parquet(path, columns=["id_cliente", "pc1", "pc2", "cluster_id"])
    if len(df) > SCATTER_SAMPLE:
        df = df.sample(SCATTER_SAMPLE, random_state=42)
    return df.to_dict(orient="records")


def segmentation_cache_mtime() -> float:
    """Hora de modificación de artefactos de segmentación."""
    mtimes = []
    for name in ("segmentacion_meta.json", "segmentacion_scatter.json"):
        p = ML_DIR / name
        if p.exists():
            mtimes.append(p.stat().st_mtime)
    return max(mtimes) if mtimes else 0.0
