"""Aísla las pruebas de los archivos locales de César (.env y respuestas guardadas para la demo)."""
import pytest


@pytest.fixture(autouse=True)
def sin_archivos_locales(monkeypatch, tmp_path):
    from primera_llamada import agente, demo
    monkeypatch.setattr(agente, "ARCHIVO_ENV", tmp_path / "no-existe.env")
    monkeypatch.setattr(demo, "ARCHIVO", tmp_path / "no-existe.json")
