"""
Recomendador por co-ocurrencia de categorías en canastas.
Evita Apriori con one-hot gigante (OOM con ~1M tickets).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import pandas as pd

from src.etl.load_transactions import (
    VALID_CATEGORY_MAX,
    _load_categories,
    _load_product_to_categories,
    resolve_ticket_categories,
)

ML_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "ml"
MAX_BASKETS_TRAIN = 80_000
MIN_CONFIDENCE = 0.08
RULES_PER_ANTECEDENT = 25


def _basket_categories(row: pd.Series, prod_map: dict[int, list[int]]) -> list[int]:
    raw = [int(c) for c in str(row["categorias"]).split() if c.strip().isdigit()]
    cats = resolve_ticket_categories(raw, int(row["id_tienda"]), prod_map)
    return sorted({c for c in cats if 1 <= c <= VALID_CATEGORY_MAX})


def train_recommender(canastas: pd.DataFrame) -> dict:
    ML_DIR.mkdir(parents=True, exist_ok=True)
    cats_map = _load_categories()
    prod_map = _load_product_to_categories()

    work = canastas
    if len(work) > MAX_BASKETS_TRAIN:
        work = work.sample(MAX_BASKETS_TRAIN, random_state=42)

    pair_counts: Counter = Counter()
    cat_counts: Counter = Counter()
    n_baskets = 0

    for _, row in work.iterrows():
        items = _basket_categories(row, prod_map)
        if len(items) < 2:
            continue
        n_baskets += 1
        for c in items:
            cat_counts[c] += 1
        for a, b in combinations(items, 2):
            pair_counts[(a, b)] += 1

    if n_baskets < 100:
        raise ValueError("Muy pocas canastas para reglas de asociación")

    rules_out: list[dict] = []
    by_cat_raw: dict[int, list[dict]] = defaultdict(list)

    for (a, b), count_ab in pair_counts.items():
        sup_ab = count_ab / n_baskets
        sup_a = cat_counts[a] / n_baskets
        sup_b = cat_counts[b] / n_baskets
        denom = sup_a * sup_b
        lift = sup_ab / denom if denom > 0 else 0.0

        conf_a_b = count_ab / cat_counts[a] if cat_counts[a] else 0.0
        if conf_a_b >= MIN_CONFIDENCE:
            rule = {
                "antecedents": [a],
                "consequents": [b],
                "support": round(sup_ab, 4),
                "confidence": round(conf_a_b, 4),
                "lift": round(lift, 4),
            }
            by_cat_raw[a].append(rule)

        conf_b_a = count_ab / cat_counts[b] if cat_counts[b] else 0.0
        if conf_b_a >= MIN_CONFIDENCE:
            rule = {
                "antecedents": [b],
                "consequents": [a],
                "support": round(sup_ab, 4),
                "confidence": round(conf_b_a, 4),
                "lift": round(lift, 4),
            }
            by_cat_raw[b].append(rule)

    by_cat: dict[int, list] = {}
    for cat_id, rules in by_cat_raw.items():
        rules.sort(key=lambda r: (-r["lift"], -r["confidence"]))
        by_cat[cat_id] = rules[:RULES_PER_ANTECEDENT]
        rules_out.extend(by_cat[cat_id])

    rules_out.sort(key=lambda r: (-r["lift"], -r["confidence"]))

    meta = {
        "n_rules": len(rules_out),
        "n_baskets_train": n_baskets,
        "min_confidence": MIN_CONFIDENCE,
        "metodo": "co-ocurrencia por par de categorías",
        "nota": "Recomendaciones por categoría (SKU mapeados vía ProductCategory.csv).",
        "categorias": {str(k): v for k, v in cats_map.items()},
    }
    (ML_DIR / "reglas_asociacion.json").write_text(
        json.dumps(
            {
                "rules": rules_out,
                "by_antecedent": {str(k): v for k, v in by_cat.items()},
                "meta": meta,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return meta


def _load_rules() -> tuple[list[dict], dict[str, list]]:
    path = ML_DIR / "reglas_asociacion.json"
    if not path.exists():
        return [], {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("rules", []), data.get("by_antecedent", {})


def _cat_name(cat_id: int) -> str:
    return _load_categories().get(cat_id, f"Categoría {cat_id}")


def recommend_for_client(
    id_cliente: int,
    canastas: pd.DataFrame,
    top_n: int = 8,
) -> list[dict]:
    _, by_cat = _load_rules()
    if not by_cat:
        return []

    cli = canastas[canastas["id_cliente"] == id_cliente]
    if cli.empty:
        return []

    prod_map = _load_product_to_categories()
    bought: set[int] = set()
    for _, row in cli.iterrows():
        bought.update(_basket_categories(row, prod_map))

    scores: dict[int, float] = defaultdict(float)
    for cat in bought:
        for rule in by_cat.get(str(cat), []):
            for cons in rule["consequents"]:
                if cons not in bought and 1 <= cons <= VALID_CATEGORY_MAX:
                    scores[cons] += rule["lift"] * rule["confidence"]

    ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_n]
    return [
        {
            "id_categoria": cid,
            "nombre_categoria": _cat_name(cid),
            "score": round(sc, 3),
            "motivo": "Suele comprarse junto a categorías de tu historial",
        }
        for cid, sc in ranked
    ]


def recommend_for_category(id_categoria: int, top_n: int = 8) -> list[dict]:
    _, by_cat = _load_rules()
    rules = by_cat.get(str(id_categoria), [])
    if not rules:
        return []

    scores: dict[int, float] = defaultdict(float)
    for rule in rules:
        for cons in rule["consequents"]:
            if cons != id_categoria and 1 <= cons <= VALID_CATEGORY_MAX:
                scores[cons] += rule["lift"]

    ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_n]
    out = []
    for cid, sc in ranked:
        confs = [r["confidence"] for r in rules if cid in r["consequents"]]
        out.append(
            {
                "id_categoria": cid,
                "nombre_categoria": _cat_name(cid),
                "score": round(sc, 3),
                "confidence": round(max(confs), 3) if confs else 0,
                "motivo": f"Comprada frecuentemente junto a {_cat_name(id_categoria)}",
            }
        )
    return out


def load_recommender_meta() -> dict | None:
    path = ML_DIR / "reglas_asociacion.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("meta")
