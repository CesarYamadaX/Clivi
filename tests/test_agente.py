import json

import openai
try:
    import httpx2 as httpx
except ImportError:  # versiones anteriores de openai usan httpx
    import httpx

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
    c, fuente = preparar_contacto(LEAD, client=cliente_falso(enviado), modelo="gpt-6-luna")
    assert fuente == "ia" and isinstance(c, Contacto) and c.canal_recomendado == "llamada"
    req = enviado[0]
    assert req["model"] == "gpt-6-luna"
    assert req["response_format"]["type"] == "json_schema"
    assert "L01738" in req["messages"][1]["content"] and "11.9 horas" in req["messages"][1]["content"]


def test_sin_credenciales(monkeypatch):
    for v in ["OPENAI_API_KEY", "OPENROUTER_API_KEY"]:
        monkeypatch.delenv(v, raising=False)
    c, fuente = preparar_contacto(LEAD)
    assert fuente.startswith("plantilla") and "control de peso" in c.whatsapp


def test_clave_invalida():
    def manejar(request):
        return httpx.Response(401, json={"error": {"type": "invalid_request_error", "code": "invalid_api_key", "message": "bad"}})
    cli = openai.OpenAI(api_key="x", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(manejar)))
    c, fuente = preparar_contacto(LEAD, client=cli)
    assert fuente == "plantilla: la clave de API no es válida"


def test_clave_openrouter():
    from primera_llamada.agente import crear_cliente
    cli, modelo = crear_cliente("sk-or-v1-prueba")
    assert str(cli.base_url).startswith("https://openrouter.ai/api/v1") and modelo == "openai/gpt-6-luna"
    cli, modelo = crear_cliente("sk-prueba")
    assert "openai.com" in str(cli.base_url) and modelo == "gpt-6-luna"


# ---------------------------------------------------------------- casos de error y reglas del mensaje
import re

import pytest

from primera_llamada.agente import plantilla


def _cliente(manejar):
    return openai.OpenAI(api_key="x", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(manejar)))


def _respuesta(contenido, refusal=None):
    return httpx.Response(200, json={
        "id": "c", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "refusal": refusal, "content": contenido}}]})


@pytest.mark.parametrize("manejar, motivo", [
    (lambda r: httpx.Response(404, json={"error": {"message": "no"}}), "no está disponible"),
    (lambda r: httpx.Response(429, json={"error": {"message": "lento"}}), "límite de uso"),
    (lambda r: httpx.Response(500, json={"error": {"message": "caído"}}), "error de la API (500)"),
    (lambda r: (_ for _ in ()).throw(httpx.ConnectError("sin red")), "sin conexión"),
    (lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("lento")), "tardó demasiado"),
    (lambda r: _respuesta("esto no es json"), "plantilla"),
    (lambda r: _respuesta('{"canal_recomendado": "fax"}'), "plantilla"),
    (lambda r: _respuesta(None, refusal="No puedo ayudar"), "no devolvió una respuesta válida"),
])
def test_fallas_de_la_api_caen_a_plantilla(manejar, motivo):
    c, fuente = preparar_contacto(LEAD, client=_cliente(manejar), modelo="m")
    assert fuente.startswith("plantilla") and motivo in fuente
    assert isinstance(c, Contacto) and c.whatsapp


def frases(texto):
    return [f for f in re.split(r"(?<=[.!?])\s+", texto.strip()) if f]


@pytest.mark.parametrize("horas", [0.1, 5, 13, 40])
@pytest.mark.parametrize("prioridad", ["alta", "media", "baja"])
def test_plantilla_cumple_reglas(horas, prioridad):
    c = plantilla({**LEAD, "horas_esperando": horas, "prioridad": prioridad})
    assert len(frases(c.whatsapp)) <= 3 and c.whatsapp.endswith("?")
    assert c.canal_recomendado == ("llamada" if prioridad == "alta" else "whatsapp")
    assert len(c.preguntas) == 3 and len(c.objeciones) == 2
    assert ("Perdón" in c.whatsapp) == (horas >= 12)


def test_revision_detecta_problemas():
    from primera_llamada.revision import revisar
    lead = {**LEAD, "horas_esperando": 20}
    malo = Contacto(canal_recomendado="whatsapp", por_que_canal="x",
                    whatsapp="Hola Mariana. Soy de Clivi. Con nosotros bajarás 10 kilos. Tu nutrióloga te atiende. Cuesta $999.",
                    guion_apertura="Hola Mariana, ¿cómo estás?", preguntas=["a"], objeciones=["a", "b", "c"],
                    si_no_contesta="Reintenta.")
    p = " | ".join(revisar(malo, lead))
    for esperado in ["frases", "no termina en pregunta", "1 preguntas", "3 objeciones",
                     "promesa", "nutrióloga", "nombre inventado", "$999", "no recomienda llamada", "12 h", "objetivo"]:
        assert esperado in p, esperado


@pytest.mark.parametrize("horas", [0.1, 13])
@pytest.mark.parametrize("objetivo", ["control de peso", "diabetes tipo 2"])
def test_plantilla_pasa_la_revision(horas, objetivo):
    from primera_llamada.revision import revisar
    lead = {**LEAD, "horas_esperando": horas, "objetivo": objetivo}
    assert revisar(plantilla(lead), lead) == []


def test_revision_reglas_de_estilo():
    """Casos reales de la primera prueba con la IA (22 nov) que antes pasaban."""
    from primera_llamada.revision import revisar
    base = dict(canal_recomendado="whatsapp", por_que_canal="x", preguntas=["a", "b", "c"],
                objeciones=["a", "b"], si_no_contesta="x")
    lead = {**LEAD, "prioridad": "baja", "horas_esperando": 15.7, "anuncio": "Imagen plan mensual"}
    c = Contacto(**base, whatsapp="Hola, vi que llegaste por el anuncio de Meta del plan mensual y te interesa "
                                  "el control de peso. Disculpa la espera. ¿Te cuento más por aquí?",
                 guion_apertura="Hola, te contacto de Clivi por tu registro de control de peso.")
    p = " | ".join(revisar(c, lead))
    assert "no dice que es de Clivi" in p and "Meta" in p and "no termina en pregunta" in p
    lead = {**LEAD, "prioridad": "media", "horas_esperando": 3.2}
    c = Contacto(**base, whatsapp="Hola, soy de Clivi; una disculpa por la demora. Me comentaste que te interesa "
                                  "el control de peso. ¿Te llamo?",
                 guion_apertura="Hola, te llamo de Clivi por el control de peso, ¿tienes un minuto?")
    p = " | ".join(revisar(c, lead))
    assert "conversación previa" in p and "poco esperando" in p
