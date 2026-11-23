"""Registro de resultados: se guarda, se reemplaza y se resume por prioridad."""
import pytest
from streamlit.testing.v1 import AppTest

from primera_llamada import registro
from tests.test_app import APP, _app


def _fila(lead, resultado, prioridad="alta", hora="09:00"):
    return {"dia": "2026-11-09", "hora": hora, "lead_id": lead, "asesor": "Asesor A", "prioridad": prioridad,
            "probabilidad": 0.1, "canal_recomendado": "llamada", "fuente_mensaje": "ia", "resultado": resultado}


def test_registrar_reemplaza_y_resume(tmp_path):
    ruta = tmp_path / "r.csv"
    assert registro.leer(ruta).empty
    registro.registrar(_fila("L1", "no_contesto"), ruta)
    registro.registrar(_fila("L1", "compro"), ruta)            # mismo lead, día y hora: reemplaza
    registro.registrar(_fila("L1", "contesto", hora="15:00"), ruta)  # otra hora: fila nueva
    registro.registrar(_fila("L2", "no_interesado", "baja"), ruta)
    t = registro.leer(ruta)
    assert len(t) == 3 and t[t.hora == "09:00"].resultado.tolist() == ["compro", "no_interesado"]
    r = registro.resumen(t)
    assert r.prioridad.tolist() == ["alta", "baja"]
    assert r.loc[0, "compraron"] == 1 and r.loc[0, "contestaron"] == 2 and r.loc[1, "contestaron"] == 1


def test_resultado_desconocido(tmp_path):
    with pytest.raises(ValueError):
        registro.registrar(_fila("L1", "tal_vez"), tmp_path / "r.csv")


def test_archivo_roto(tmp_path):
    ruta = tmp_path / "r.csv"
    ruta.write_text("esto,no\nes,el formato\n", encoding="utf-8")
    assert registro.leer(ruta).empty


def test_app_registra_resultado(monkeypatch):
    at = _app(monkeypatch)
    [b for b in at.button if b.label == "✅ Compró"][0].click().run()
    assert not at.exception
    t = registro.leer()
    assert len(t) == 1 and t.resultado.iloc[0] == "compro" and t.prioridad.iloc[0] == "alta"
    assert any("Compró" in c.value for c in at.caption)
    # en la pestaña de validación aparece el resumen
    assert any(m.value == "Compraron" or "Compraron" in str(m.value) for m in at.markdown)
