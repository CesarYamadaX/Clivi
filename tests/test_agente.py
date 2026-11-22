import json

import openai
import httpx2 as httpx

from primera_llamada.agente import Contacto, preparar_contacto

LEAD = {"lead_id": "L01738", "canal": "Google", "anuncio": "Busqueda tratamiento peso", "objetivo": "control de peso",
        "plan_de_interes": "1299", "estado": "CDMX", "edad": "39", "horas_esperando": 11.9,
        "prioridad": "alta", "probabilidad": 0.161, "hora_actual": "09:00"}

RESPUESTA = {
    "canal_recomendado": "llamada", "por_que_canal": "Prioridad alta.",
    "whatsapp": "Hola, soy de Clivi. ¿Te llamo hoy?", "guion_apertura": "Hola, te llamo de Clivi.",
    "preguntas": ["a", "b", "c"], "objeciones": ["caro → plan base", "tiempo → app"],
    "si_no_contesta": "Reintenta a las 13:00.",
}


def cliente_falso(capturado):
    def manejar(request):
        capturado.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": "gpt-6-luna",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "refusal": None,
                                     "content": json.dumps(RESPUESTA, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}})
    return openai.OpenAI(api_key="prueba", http_client=httpx.Client(transport=httpx.MockTransport(manejar)))


def test_con_ia():
    enviado = []
    c, fuente = preparar_contacto(LEAD, cliente_falso(enviado))
    assert fuente == "ia" and isinstance(c, Contacto) and c.canal_recomendado == "llamada"
    req = enviado[0]
    assert req["model"] == "gpt-6-luna"
    assert req["response_format"]["type"] == "json_schema"
    assert "L01738" in req["messages"][1]["content"] and "11.9 horas" in req["messages"][1]["content"]


def test_sin_credenciales(monkeypatch):
    for v in ["OPENAI_API_KEY", "OPENAI_ADMIN_KEY"]:
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("HOME", "/nonexistent")
    c, fuente = preparar_contacto(LEAD, None)
    assert fuente.startswith("plantilla") and "control de peso" in c.whatsapp


def test_clave_invalida():
    def manejar(request):
        return httpx.Response(401, json={"error": {"type": "invalid_request_error", "code": "invalid_api_key", "message": "bad"}})
    cli = openai.OpenAI(api_key="x", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(manejar)))
    c, fuente = preparar_contacto(LEAD, cli)
    assert fuente == "plantilla: la clave de API no es válida"
