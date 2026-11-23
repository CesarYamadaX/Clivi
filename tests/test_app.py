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
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-clave-falsa")
    at.run()
    assert any("IA conectada" in c.value for c in at.caption)
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["contacto"][2].startswith("plantilla")


def test_respuesta_guardada_para_la_demo(monkeypatch, tmp_path):
    """Con una respuesta guardada, la app la muestra sin llamar a la IA (aquí no hay clave)."""
    import json
    from primera_llamada import demo
    from primera_llamada.agente import plantilla
    at = _app(monkeypatch)
    at.button[0].click().run()
    lead_id = at.session_state["contacto"][0]
    assert at.session_state["contacto"][2].startswith("plantilla")
    # guardamos para todos los leads de la lista una respuesta reconocible
    import guardar_demo
    respuestas = {}
    for lead in guardar_demo.leads_demo():
        c = plantilla(lead)
        c.whatsapp = "¡Hola, soy tu asesor de Clivi, respuesta guardada! ¿Te llamo?"
        respuestas[demo.llave(lead)] = c.model_dump()
    archivo = tmp_path / "respuestas_demo.json"
    archivo.write_text(json.dumps({"respuestas": respuestas}), encoding="utf-8")
    monkeypatch.setattr(demo, "ARCHIVO", archivo)
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.button[0].click().run()
    assert not at.exception
    lid, c, fuente = at.session_state["contacto"]
    assert lid == lead_id and fuente == "ia (guardada)" and "respuesta guardada" in c.whatsapp
    # apagando el interruptor intenta en vivo; sin IA disponible, usa la guardada de respaldo
    [t for t in at.toggle if t.label == "Usar respuestas guardadas"][0].set_value(False).run()
    at.button[0].click().run()
    assert not at.exception and at.session_state["contacto"][2] == "ia (guardada)"


def test_vista_de_un_asesor(monkeypatch):
    """Con «Ver como» un asesor, la lista principal solo muestra sus leads y el equipo queda en otra pestaña."""
    at = _app(monkeypatch)
    vista = [s for s in at.selectbox if s.label == "Ver como"][0]
    asesor = vista.options[1]
    vista.set_value(asesor).run()
    assert not at.exception
    assert any(t.label.startswith("Mis leads") for t in at.tabs)
    assert any(t.label.startswith("Todo el equipo") for t in at.tabs)
    lead = [s for s in at.selectbox if s.label == "Lead"][0]
    assert all(asesor in o for o in lead.options)


def test_lead_elegido_en_la_lista_abre_el_panel(monkeypatch):
    """Picar una fila de la lista deja el lead elegido: se abre su panel ahí mismo y en Preparar contacto."""
    at = _app(monkeypatch)
    lead = [s for s in at.selectbox if s.label == "Lead"][0]
    tercero = lead.options[2].split(" · ")[1]
    at.session_state["lead_sel"] = tercero
    at.run()
    assert not at.exception
    assert any(b.key == "lista_preparar" for b in at.button)
    [b for b in at.button if b.key == "lista_preparar"][0].click().run()
    assert not at.exception
    assert at.session_state["contacto"][0] == tercero
