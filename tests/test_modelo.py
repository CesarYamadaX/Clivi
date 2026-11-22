from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from primera_llamada.modelo import entrenar, leer_leads, lista_del_dia, repartir, tramo, validar

DATOS = Path(__file__).parents[1] / "data" / "leads_ficticios.csv"
ASESORES = ["Asesor A", "Asesor B", "Asesor C", "Asesor D", "Asesor E"]


@pytest.fixture(scope="module")
def leads():
    return leer_leads(DATOS)


def test_limpieza(leads):
    _, r = leads
    assert r == {"registros": 1811, "duplicados": 70, "fechas_ddmm": 109, "personas": 1741}


def test_tramos():
    assert list(tramo([0.1, 0.25, 0.5, 1, 11.9, 12, 40])) == [0, 1, 1, 2, 2, 3, 3]


def test_lista_9_nov(leads):
    df, _ = leads
    lista, modelo = lista_del_dia(df, datetime(2026, 11, 9), 9, ASESORES)
    assert len(lista) == 42
    assert lista.probabilidad.is_monotonic_decreasing
    assert lista.lead_id.iloc[0] == "L01738"
    assert modelo.efecto[0] > modelo.efecto[-1]


def test_reparto_serpiente():
    lista = pd.DataFrame({"x": range(6)})
    assert list(repartir(lista, ["A", "B", "C"]).asignado) == ["A", "B", "C", "C", "B", "A"]


def test_no_usa_el_futuro(leads):
    df, _ = leads
    dia = datetime(2026, 10, 20)
    antes = entrenar(df[df.reg < dia])
    assert sum(antes.leads_anuncio.values()) == (df.reg < dia).sum()


def test_validacion(leads):
    df, _ = leads
    v = validar(df)
    assert (v["primera_llamada"], v["orden_real"], v["orden_llegada"], v["ventas"]) == (21, 13, 6, 30)


def test_archivo_sin_columnas(tmp_path):
    p = tmp_path / "malo.csv"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        leer_leads(p)
