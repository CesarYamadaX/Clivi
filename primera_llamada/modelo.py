"""
Lógica de Primera Llamada.

1. leer_leads()      lee el CSV, corrige fechas DD/MM y quita teléfonos repetidos.
2. entrenar()        aprende la tasa de venta por anuncio y el efecto del tiempo esperando.
3. cola()            arma los leads que siguen sin primera llamada a una hora dada.
4. priorizar()       calcula la probabilidad de venta si se les llama ahora y los ordena.
5. repartir()        reparte la lista entre los asesores que trabajan (en serpiente).
6. validar()         revisa en días pasados qué tanto pone las ventas arriba de la lista.

probabilidad = tasa de venta del anuncio × efecto del tiempo esperando
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

K = 30                                  # fuerza con la que un anuncio con pocos datos se acerca a su canal
CORTES_H = [0, 0.25, 1, 12, np.inf]     # cortes del tiempo esperando, en horas
ETIQUETAS = ["en menos de 15 min", "entre 15 y 60 min", "entre 1 y 12 h", "después de 12 h"]
VENTANA_H = 48                          # solo se consideran leads de las últimas 48 h
COLUMNAS = ["lead_id", "fecha_registro", "canal", "telefono", "resultado"]


# ---------------------------------------------------------------- 1. datos
def _fechas(col: pd.Series) -> pd.Series:
    """Acepta AAAA-MM-DD HH:MM y DD/MM/AAAA HH:MM (las de Referido vienen así)."""
    col = col.fillna("").astype(str).str.strip()
    iso = col.str.match(r"\d{4}-")
    a = pd.to_datetime(col.where(iso), format="%Y-%m-%d %H:%M", errors="coerce")
    b = pd.to_datetime(col.where(~iso & (col != "")), format="%d/%m/%Y %H:%M", errors="coerce")
    return a.fillna(b)


def leer_leads(fuente) -> tuple[pd.DataFrame, dict]:
    """Devuelve (leads limpios, resumen de limpieza). `fuente` es una ruta o un archivo abierto."""
    df = pd.read_csv(fuente, dtype=str)
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        raise ValueError(f"Al archivo le faltan columnas: {', '.join(faltan)}")
    ddmm = int(df.fecha_registro.fillna("").str.match(r"\d{1,2}/").sum())
    df["reg"] = _fechas(df.fecha_registro)
    df["con"] = _fechas(df.get("primer_contacto", pd.Series(index=df.index, dtype=str)))
    df = df[df.reg.notna()].sort_values("reg", kind="stable")
    total = len(df)
    df = df[~df.duplicated("telefono", keep="first")].copy()
    df["anuncio"] = df.get("anuncio", pd.Series(index=df.index, dtype=str)).fillna("(sin anuncio)")
    df["venta"] = (df.resultado == "venta").astype(int)
    df = df.reset_index(drop=True)
    resumen = {"registros": total, "duplicados": total - len(df), "fechas_ddmm": ddmm, "personas": len(df)}
    return df, resumen


# ---------------------------------------------------------------- 2. modelo
@dataclass
class Modelo:
    general: float
    canal: dict          # canal -> tasa
    anuncio: dict        # (canal, anuncio) -> tasa
    leads_anuncio: dict  # (canal, anuncio) -> número de leads
    efecto: np.ndarray   # multiplicador por tramo de espera

    def base(self, canal: str, anuncio: str) -> float:
        return self.anuncio.get((canal, anuncio), self.canal.get(canal, self.general))

    def tabla_anuncios(self) -> pd.DataFrame:
        t = pd.DataFrame([{"canal": c, "anuncio": a, "leads": self.leads_anuncio[(c, a)], "tasa_venta": p}
                          for (c, a), p in self.anuncio.items()])
        return t.sort_values("tasa_venta", ascending=False, ignore_index=True)

    def tabla_efecto(self) -> pd.DataFrame:
        return pd.DataFrame({"si se le llama": ETIQUETAS, "efecto": self.efecto})


def tramo(horas) -> np.ndarray:
    h = np.asarray(horas, dtype=float)
    return np.clip(np.searchsorted(CORTES_H, h, side="right") - 1, 0, len(ETIQUETAS) - 1)


def entrenar(historia: pd.DataFrame) -> Modelo:
    """Aprende solo de `historia` (leads con resultado conocido)."""
    g = historia.venta.mean() if len(historia) else 0.0
    ch = historia.groupby("canal").venta.agg(["sum", "size"])
    p_canal = ((ch["sum"] + K * g) / (ch["size"] + K)).to_dict()
    ad = historia.groupby(["canal", "anuncio"]).venta.agg(["sum", "size"])
    p_ad, n_ad = {}, {}
    for (c, a), fila in ad.iterrows():
        p_ad[(c, a)] = (fila["sum"] + K * p_canal[c]) / (fila["size"] + K)
        n_ad[(c, a)] = int(fila["size"])

    m = Modelo(g, p_canal, p_ad, n_ad, np.ones(len(ETIQUETAS)))
    # Efecto del tiempo: ventas observadas / ventas que esperaríamos solo por el anuncio
    c = historia[historia.con.notna()]
    if len(c):
        espera = (c.con - c.reg).dt.total_seconds() / 3600
        t = tramo(espera)
        base = np.array([m.base(x, y) for x, y in zip(c.canal, c.anuncio)])
        obs = np.bincount(t, weights=c.venta.to_numpy(), minlength=len(ETIQUETAS))
        esp = np.bincount(t, weights=base, minlength=len(ETIQUETAS))
        m.efecto = np.where(esp > 0, obs / np.where(esp > 0, esp, 1), 1.0)
    return m


# ---------------------------------------------------------------- 3-5. lista del día
def cola(leads: pd.DataFrame, ahora: datetime) -> pd.DataFrame:
    """Leads de las últimas 48 h que a esta hora aún no reciben su primera llamada."""
    desde = ahora - timedelta(hours=VENTANA_H)
    sin_llamar = leads.con.isna() | (leads.con >= ahora)
    return leads[(leads.reg < ahora) & (leads.reg >= desde) & sin_llamar].copy()


def prioridad(p: float) -> str:
    return "alta" if p >= 0.08 else "media" if p >= 0.03 else "baja"


def _horas(h: float) -> str:
    return f"{round(h * 60)} min" if h < 1 else (f"{h:.1f} h" if h < 24 else f"{round(h)} h")


def razon(fila, modelo: Modelo) -> str:
    nombre = fila.canal if fila.anuncio == "(sin anuncio)" else fila.anuncio
    pct = round(fila.tasa_anuncio * 100)
    s = f"{nombre}: {'menos de 1' if pct < 1 else pct} de cada 100 leads compran."
    w = fila.horas_esperando
    if w < 0.25:
        s += f" Acaba de llegar: si se le llama en {max(1, round(15 - w * 60))} min su probabilidad sube ×{modelo.efecto[0]:.1f}."
    elif w < 12:
        s += f" Lleva {_horas(w)}. Le quedan {_horas(12 - w)} antes de que pase de 12 h y su probabilidad caiga."
    else:
        s += f" Lleva {_horas(w)}. Ya pasó de 12 h, hay que intentarlo hoy antes de perderlo."
    return s


def priorizar(q: pd.DataFrame, modelo: Modelo, ahora: datetime) -> pd.DataFrame:
    q = q.copy()
    q["horas_esperando"] = (ahora - q.reg).dt.total_seconds() / 3600
    q["tasa_anuncio"] = [modelo.base(c, a) for c, a in zip(q.canal, q.anuncio)]
    q["probabilidad"] = q.tasa_anuncio * modelo.efecto[tramo(q.horas_esperando)]
    q = q.sort_values(["probabilidad", "reg"], ascending=[False, True], ignore_index=True)
    q["prioridad"] = q.probabilidad.map(prioridad)
    q["razon"] = [razon(f, modelo) for f in q.itertuples()]
    q.insert(0, "orden", range(1, len(q) + 1))
    return q


def repartir(lista: pd.DataFrame, asesores: list[str]) -> pd.DataFrame:
    """En serpiente (A B C C B A ...) para que todos reciban leads buenos."""
    lista = lista.copy()
    n = len(asesores)
    if n == 0:
        lista["asignado"] = "Sin asignar"
        return lista
    i = np.arange(len(lista))
    vuelta, pos = i // n, i % n
    lista["asignado"] = [asesores[p if v % 2 == 0 else n - 1 - p] for v, p in zip(vuelta, pos)]
    return lista


def lista_del_dia(leads: pd.DataFrame, dia: datetime, hora: int, asesores: list[str]):
    """Atajo: entrena con días anteriores, arma la cola, la ordena y la reparte."""
    inicio = datetime(dia.year, dia.month, dia.day)
    ahora = inicio + timedelta(hours=hora)
    modelo = entrenar(leads[leads.reg < inicio])
    return repartir(priorizar(cola(leads, ahora), modelo, ahora), asesores), modelo


# ---------------------------------------------------------------- 6. validación
def validar(leads: pd.DataFrame, hora: int = 9, dias_minimos: int = 14) -> dict:
    """
    Para cada mañana después de los primeros `dias_minimos` días:
    entrena solo con días anteriores, arma la cola de las `hora`:00 y cuenta
    cuántas de las ventas quedan en el primer tercio con tres órdenes distintos.
    """
    primero = leads.reg.min().normalize()
    ultimo = leads.reg.max().normalize()
    r = {"primera_llamada": 0, "orden_real": 0, "orden_llegada": 0, "ventas": 0, "mananas": 0, "leads": 0}
    for dia in pd.date_range(primero + pd.Timedelta(days=dias_minimos), ultimo):
        ahora = dia + pd.Timedelta(hours=hora)
        q = cola(leads, ahora)
        if q.empty:
            continue
        k = int(np.ceil(len(q) / 3))
        modelo = entrenar(leads[leads.reg < dia])
        ordenes = {
            "primera_llamada": priorizar(q, modelo, ahora),
            "orden_real": q.sort_values("con", na_position="last", kind="stable"),
            "orden_llegada": q.sort_values("reg", kind="stable"),
        }
        for nombre, o in ordenes.items():
            r[nombre] += int(o.venta.iloc[:k].sum())
        r["ventas"] += int(q.venta.sum())
        r["mananas"] += 1
        r["leads"] += len(q)
    return r
