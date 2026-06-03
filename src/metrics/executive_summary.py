"""
Métricas del Resumen Ejecutivo.
Trabaja sobre tablas agregadas (no sobre hechos completos).
"""
from __future__ import annotations
import pandas as pd

def top_productos_from_agg(por_categoria: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if por_categoria.empty:
        return pd.DataFrame(columns=["id_categoria", "nombre_categoria", "unidades"])
    return (
        por_categoria.groupby(["id_categoria", "nombre_categoria"], as_index=False)["cantidad"]
        .sum()
        .sort_values("cantidad", ascending=False)
        .head(n)
        .rename(columns={"cantidad": "unidades"})
    )

def top_clientes_from_agg(por_cliente: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if por_cliente.empty:
        return pd.DataFrame(columns=["id_cliente", "n_transacciones"])
    return (
        por_cliente.groupby("id_cliente", as_index=False)["n_transacciones"]
        .sum()
        .sort_values("n_transacciones", ascending=False)
        .head(n)
    )

def ventas_por_dia_from_agg(por_dia: pd.DataFrame) -> pd.DataFrame:
    if por_dia.empty:
        return pd.DataFrame(columns=["fecha", "n_transacciones"])
    return (
        por_dia.groupby("fecha", as_index=False)
        .agg(n_transacciones=("n_transacciones", "sum"))
        .sort_values("fecha")
    )

def ventas_por_semana_from_agg(por_semana: pd.DataFrame) -> pd.DataFrame:
    if por_semana.empty:
        return pd.DataFrame(columns=["anio_semana", "n_transacciones"])
    return (
        por_semana.groupby("anio_semana", as_index=False)
        .agg(n_transacciones=("n_transacciones", "sum"))
        .sort_values("anio_semana")
    )

def categorias_por_volumen_from_agg(por_categoria: pd.DataFrame) -> pd.DataFrame:
    if por_categoria.empty:
        return pd.DataFrame(columns=["nombre_categoria", "unidades"])
    return (
        por_categoria.groupby("nombre_categoria", as_index=False)["cantidad"]
        .sum()
        .sort_values("cantidad", ascending=False)
        .rename(columns={"cantidad": "unidades"})
    )

def actividad_dia_mes_from_agg(por_dia: pd.DataFrame) -> pd.DataFrame:
    if por_dia.empty:
        return pd.DataFrame()
    return (
        por_dia.groupby(["dia_semana", "mes"], as_index=False)
        .agg(n_transacciones=("n_transacciones", "sum"))
    )


def actividad_por_dia_semana_from_agg(por_dia: pd.DataFrame) -> pd.DataFrame:
    """Suma transacciones por día de la semana (Lunes–Domingo) en el periodo filtrado."""
    if por_dia.empty:
        return pd.DataFrame(columns=["dia_semana", "n_transacciones"])
    return (
        por_dia.groupby("dia_semana", as_index=False)
        .agg(n_transacciones=("n_transacciones", "sum"))
    )
