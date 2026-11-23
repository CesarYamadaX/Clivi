"""
Registro de lo que pasó con cada lead después del primer contacto.

Cada vez que un asesor marca un resultado se agrega una fila a
data/resultados_registrados.csv (el archivo no se sube a git). Con estas filas,
más adelante se puede recalibrar la prioridad con resultados reales y juntar
ejemplos buenos y malos para afinar la IA.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

ARCHIVO = Path(__file__).resolve().parents[1] / "data" / "resultados_registrados.csv"
RESULTADOS = {"contesto": "Contestó", "no_contesto": "No contestó",
              "compro": "Compró", "no_interesado": "No interesado"}
COLUMNAS = ["registrado", "dia", "hora", "lead_id", "asesor", "prioridad", "probabilidad",
            "canal_recomendado", "fuente_mensaje", "resultado"]


def ahora() -> datetime:
    """Hora de la Ciudad de México (el servidor publicado corre en UTC)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Mexico_City")).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def leer(ruta: Optional[Path] = None) -> pd.DataFrame:
    ruta = ruta or ARCHIVO
    try:
        tabla = pd.read_csv(ruta, dtype={"lead_id": str})
        return tabla[COLUMNAS]
    except (OSError, ValueError, KeyError):
        return pd.DataFrame(columns=COLUMNAS)


def registrar(fila: dict, ruta: Optional[Path] = None) -> pd.DataFrame:
    """Agrega una fila. Si el lead ya tenía un resultado para ese día y hora, lo reemplaza."""
    if fila.get("resultado") not in RESULTADOS:
        raise ValueError(f"resultado desconocido: {fila.get('resultado')}")
    ruta = ruta or ARCHIVO
    nueva = {c: fila.get(c, "") for c in COLUMNAS}
    nueva["registrado"] = f"{ahora():%Y-%m-%d %H:%M:%S}"
    tabla = leer(ruta)
    misma = (tabla.lead_id == str(nueva["lead_id"])) & (tabla.dia == nueva["dia"]) & (tabla.hora == nueva["hora"])
    tabla = pd.concat([tabla[~misma], pd.DataFrame([nueva])], ignore_index=True)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(ruta, index=False)
    return tabla


def resumen(tabla: pd.DataFrame) -> pd.DataFrame:
    """Por prioridad: cuántos se registraron, cuántos contestaron y cuántos compraron."""
    if tabla.empty:
        return pd.DataFrame(columns=["prioridad", "registrados", "contestaron", "compraron", "tasa_compra"])
    t = tabla.assign(contesto=tabla.resultado.isin(["contesto", "compro", "no_interesado"]),
                     compro=tabla.resultado.eq("compro"))
    r = (t.groupby("prioridad").agg(registrados=("lead_id", "size"), contestaron=("contesto", "sum"),
                                    compraron=("compro", "sum")).reset_index())
    r["tasa_compra"] = r.compraron / r.registrados
    orden = {"alta": 0, "media": 1, "baja": 2}
    return r.sort_values("prioridad", key=lambda s: s.map(orden).fillna(9)).reset_index(drop=True)
