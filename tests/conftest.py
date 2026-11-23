"""Aísla las pruebas de los archivos locales de César (.env, respuestas guardadas y resultados registrados)."""
import pytest


@pytest.fixture(autouse=True)
def sin_archivos_locales(monkeypatch, tmp_path):
    from primera_llamada import agente, demo, registro
    monkeypatch.setattr(agente, "ARCHIVO_ENV", tmp_path / "no-existe.env")
    monkeypatch.setattr(demo, "ARCHIVO", tmp_path / "no-existe.json")
    monkeypatch.setattr(registro, "ARCHIVO", tmp_path / "resultados.csv")
