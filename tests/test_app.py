"""La pantalla de Streamlit carga sin errores y el asistente responde con la plantilla."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parents[1] / "app.py")


def test_app_carga_y_prepara_contacto(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert len(at.tabs) >= 3
    at.button[0].click().run()
    assert not at.exception
    assert "contacto" in at.session_state


def test_modo_validacion(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.toggle[0].set_value(True).run()
    assert not at.exception


def _app(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return AppTest.from_file(APP, default_timeout=60).run()


def test_varios_dias_y_horas(monkeypatch):
    at = _app(monkeypatch)
    dia = [s for s in at.selectbox if s.label == "Día"][0]
    n = len(dia.options)
    for i in [0, n // 2, n - 1]:
        for hora in [7, 9, 14, 20]:
            [s for s in at.selectbox if s.label == "Día"][0].select_index(i)
            at.select_slider[0].set_value(hora)
            at.run()
            assert not at.exception, (i, hora)


def test_sin_asesores(monkeypatch):
    at = _app(monkeypatch)
    at.multiselect[0].set_value([]).run()
    assert not at.exception
    assert any("al menos un asesor" in w.value for w in at.warning)


def test_cambiar_de_lead_limpia_el_contacto(monkeypatch):
    at = _app(monkeypatch)
    at.button[0].click().run()
    lead_1 = at.session_state["contacto"][0]
    sel = [s for s in at.selectbox if s.label == "Lead"][0]
    sel.set_value(1).run()
    assert not at.exception
    assert not any("Empezar por" in s.value for s in at.success)
    at.button[0].click().run()
    assert at.session_state["contacto"][0] != lead_1


def test_clave_falsa_no_rompe_la_app(monkeypatch):
    at = _app(monkeypatch)
    at.text_input[0].set_value("sk-or-v1-clave-falsa").run()
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["contacto"][2].startswith("plantilla")
