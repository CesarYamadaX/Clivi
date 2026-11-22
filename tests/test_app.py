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
