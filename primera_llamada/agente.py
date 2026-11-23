"""
Asistente de seguimiento: prepara el primer contacto con cada lead.

Para cada lead de la lista decide si conviene WhatsApp o llamada, y escribe
el mensaje de WhatsApp, el guion de llamada, las objeciones probables y qué
hacer si no contesta. Usa GPT-6 Luna con salida estructurada, por OpenRouter
(clave sk-or-...) o directo con OpenAI (clave sk-...).

El modelo se puede cambiar con la variable MODELO_IA.
Si no hay clave o la llamada falla, usa una plantilla fija para que la app
siga funcionando.
"""
from __future__ import annotations

from typing import Literal

import json
import os
from pathlib import Path

import openai
from pydantic import BaseModel, Field

OPENROUTER_URL = "https://openrouter.ai/api/v1"
MODELO_OPENROUTER = "openai/gpt-6-luna"
MODELO_OPENAI = "gpt-6-luna"
TEMPERATURA = 0.4  # más bajo = respuestas más parejas entre leads
TIEMPO_MAXIMO = 45  # segundos; en una demo es mejor caer a la plantilla que dejar la pantalla congelada


def crear_cliente(clave: str) -> tuple[openai.OpenAI, str]:
    """Una clave sk-or-... va a OpenRouter; cualquier otra, directo a OpenAI."""
    if clave.startswith("sk-or-"):
        cliente = openai.OpenAI(api_key=clave, base_url=OPENROUTER_URL, timeout=TIEMPO_MAXIMO, max_retries=1,
                                default_headers={"X-Title": "Primera Llamada"})
        return cliente, os.environ.get("MODELO_IA", MODELO_OPENROUTER)
    return (openai.OpenAI(api_key=clave, timeout=TIEMPO_MAXIMO, max_retries=1),
            os.environ.get("MODELO_IA", MODELO_OPENAI))


ARCHIVO_ENV = Path(__file__).resolve().parents[1] / ".env"


def leer_env(ruta: Path | None = None) -> dict:
    """Lee un .env sencillo (CLAVE=valor por línea). No pisa variables ya definidas en la terminal."""
    valores = {}
    ruta = ruta or ARCHIVO_ENV
    if not ruta.is_file():
        return valores
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        nombre = nombre.strip().removeprefix("export ").strip()
        valores[nombre] = valor.strip().strip('"').strip("'")
    return valores


def clave_del_entorno() -> str:
    """Primero la terminal; si no, el archivo .env de la carpeta del proyecto."""
    archivo = leer_env()
    for nombre in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if os.environ.get(nombre):
            return os.environ[nombre]
    for nombre in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if archivo.get(nombre):
            return archivo[nombre]
    return ""

SISTEMA = """Eres el asistente de seguimiento de los asesores de ventas de Clivi, \
una clínica digital mexicana para control de peso y diabetes tipo 2. \
Planes mensuales: $1,299, $1,599 y $2,499 MXN. No describas servicios concretos \
(qué incluye cada plan, qué especialistas hay): eso lo explica el asesor en la llamada.

Preparas el primer contacto de un asesor con un lead que dejó sus datos en un anuncio.
Reglas:
- Español de México, cálido y directo, de tú. Nada de presión ni urgencia falsa.
- El WhatsApp tiene máximo 3 frases y termina con una pregunta fácil de contestar.
- No prometas resultados médicos (kilos, glucosa, curas) ni des consejos médicos; \
eso lo hace el equipo médico en la consulta.
- El WhatsApp llega de un número que el lead no conoce: preséntate siempre como asesor de Clivi.
- Usa lo que sabes del lead (objetivo, cuánto lleva esperando, plan que le interesó). \
Si lleva más de 12 horas esperando, discúlpate con naturalidad; si lleva menos, no te disculpes.
- Los nombres de canal y anuncio son internos ("Meta", "Carrusel resultados", "Clip musica 03"): \
no los cites. Si hace falta, di "tu registro" o "nuestro anuncio".
- No inventes datos del lead que no te dieron (por ejemplo, su nombre) ni digas que ya habló contigo \
("me comentaste"): es el primer contacto.
- La apertura de la llamada termina con una pregunta.
- Cada lead trae "pistas": úsalas. Al menos una pregunta y una objeción deben salir de las pistas \
de ese lead, no ser genéricas ("quiero pensarlo", "se me hace caro") salvo que la pista lo indique.
- Varía la primera frase del WhatsApp según el lead; no empieces siempre igual.
- Adapta las preguntas y las objeciones al lead: no son las mismas para diabetes que para peso, \
ni para un referido que para alguien que vio un anuncio. Los ejemplos muestran el tono y el largo; \
no copies sus frases."""


class Contacto(BaseModel):
    canal_recomendado: Literal["llamada", "whatsapp"] = Field(
        description="Por dónde empezar. Llamada si es prioridad alta y está en horario; si no, WhatsApp.")
    por_que_canal: str = Field(description="Una frase que explica la elección.")
    whatsapp: str = Field(description="Mensaje listo para enviar, máximo 3 frases.")
    guion_apertura: str = Field(description="Primeras 2 frases de la llamada.")
    preguntas: list[str] = Field(description="3 preguntas para entender su caso.")
    objeciones: list[str] = Field(description="2 objeciones probables, cada una con una respuesta corta: 'objeción → respuesta'.")
    si_no_contesta: str = Field(description="Qué hacer y cuándo reintentar si no contesta.")


# ---------------------------------------------------------------- pistas por tipo de lead
# Lo que un asesor con experiencia sabe de cada tipo de lead. Se calculan con reglas (no con IA)
# y se le pasan al modelo para que adapte el mensaje en vez de adivinar.
PISTAS_CANAL = {
    "Referido": "Llegó recomendado por alguien: ya confía un poco. Pregunta quién lo recomendó y qué le contó; "
                "apóyate en esa confianza.",
    "Google": "Buscó activamente en Google: tiene una necesidad concreta y está comparando. Sé directo y "
              "ofrece resolver sus dudas ya.",
    "TikTok": "Viene de TikTok: suele ser curiosidad, todavía sin decisión. Tono ligero y breve; ofrece "
              "información por WhatsApp antes que una llamada larga.",
    "Meta": "Vio un anuncio en redes y dejó sus datos, quizá de impulso: recuérdale con naturalidad qué pidió "
            "y pregunta qué le llamó la atención.",
    "Organico": "Llegó solo al sitio de Clivi: ya nos conoce algo. Pregunta cómo supo de Clivi.",
}
PISTAS_OBJETIVO = {
    "diabetes": "Busca apoyo con diabetes tipo 2: probablemente ya tiene médico. Objeción probable: "
                "\"ya tengo doctor\" → Clivi acompaña entre consultas, no sustituye a su médico. Pregunta cómo "
                "lleva hoy su control y quién le da seguimiento.",
    "peso": "Busca control de peso: probablemente ya intentó dietas u otros métodos. Objeción probable: "
            "\"ya probé de todo\" → aquí lo lleva un médico y se ajusta a su caso. Pregunta qué ha intentado "
            "y qué no le funcionó.",
}


def pistas(lead: dict) -> list:
    p = []
    canal = str(lead.get("canal") or "")
    if canal in PISTAS_CANAL:
        p.append(PISTAS_CANAL[canal])
    objetivo = str(lead.get("objetivo") or "").lower()
    for clave, texto in PISTAS_OBJETIVO.items():
        if clave in objetivo:
            p.append(texto)
    try:
        edad = int(float(lead.get("edad")))
    except (TypeError, ValueError):
        edad = None
    if edad is not None and 18 <= edad <= 100:
        if edad >= 50:
            p.append(f"Tiene {edad} años: tono cálido y respetuoso, frases claras; suele preferir una llamada "
                     "a muchos mensajes.")
        elif edad <= 30:
            p.append(f"Tiene {edad} años: tono cercano y casual; WhatsApp corto funciona mejor que una llamada fría.")
    plan = str(lead.get("plan_de_interes") or "").replace(",", "")
    if plan == "2499":
        p.append("Le interesó el plan más completo ($2,499): objeción probable de precio → habla del valor y de "
                 "que puede empezar con otro plan si lo prefiere; no lo bajes de plan de entrada.")
    elif plan == "1299":
        p.append("Le interesó el plan de entrada ($1,299): cuida el presupuesto; no intentes venderle uno más caro "
                 "en el primer contacto. Objeción probable: \"¿qué incluye?\" → eso se explica en la llamada.")
    horas = float(lead.get("horas_esperando") or 0)
    if horas < 0.25:
        p.append("Acaba de dejar sus datos (menos de 15 minutos): es el mejor momento, llama ya y dilo "
                 "(\"hace un momento dejaste tus datos\").")
    elif horas >= 24:
        p.append("Lleva más de un día esperando: discúlpate y dale una salida fácil (\"si ya no te interesa, "
                 "también está bien\").")
    hora = str(lead.get("hora_actual") or "09:00")
    try:
        h = int(hora.split(":")[0])
    except ValueError:
        h = 9
    if h >= 19 or h < 9:
        p.append(f"Son las {hora}: fuera de horario para llamar; empieza por WhatsApp y propone llamar mañana.")
    return p


def _contexto(lead: dict) -> str:
    anuncio = lead.get("anuncio") or "(sin anuncio)"
    lista = pistas(lead)
    extra = ("\nPistas para este lead (úsalas para adaptar el mensaje, sin copiarlas):\n"
             + "\n".join(f"- {x}" for x in lista)) if lista else ""
    return (
        f"Lead {lead.get('lead_id')}\n"
        f"- Llegó por: {lead.get('canal')} · {anuncio}\n"
        f"- Objetivo: {lead.get('objetivo') or 'sin dato'}\n"
        f"- Plan que le interesó: ${lead.get('plan_de_interes') or 'sin dato'} MXN al mes\n"
        f"- Estado: {lead.get('estado') or 'sin dato'} · Edad: {lead.get('edad') or 'sin dato'}\n"
        f"- Lleva esperando: {lead.get('horas_esperando', 0):.1f} horas\n"
        f"- Prioridad en la lista: {lead.get('prioridad')} "
        f"({100 * lead.get('probabilidad', 0):.1f}% de probabilidad de venta si se le llama ahora)\n"
        f"- Hora actual del asesor: {lead.get('hora_actual', '09:00')}"
        + extra
    )


# ---------------------------------------------------------------- ejemplos (few-shot)
# Dos casos resueltos "como lo haría el mejor asesor". Le enseñan al modelo el tono, el largo
# y cómo adaptar el mensaje al lead, sin tener que entrenarlo (fine-tuning).
EJEMPLOS = [
    ({"lead_id": "EJEMPLO-1", "canal": "Google", "anuncio": "Busqueda tratamiento peso", "objetivo": "control de peso",
      "plan_de_interes": "1599", "estado": "Jalisco", "edad": "34", "horas_esperando": 0.1,
      "prioridad": "alta", "probabilidad": 0.31, "hora_actual": "10:00"},
     {"canal_recomendado": "llamada",
      "por_que_canal": "Acaba de dejar sus datos y es prioridad alta: llamar en los primeros 15 minutos "
                       "es cuando más contesta y más compra.",
      "whatsapp": "¡Hola! Soy tu asesora de Clivi. Vi que acabas de dejar tus datos para control de peso; "
                  "¿te puedo marcar en 5 minutos para platicarte cómo funciona?",
      "guion_apertura": "Hola, te habla tu asesora de Clivi; te marco porque hace un momento dejaste tus datos para control "
                        "de peso. ¿Tienes 5 minutos para contarme qué estás buscando?",
      "preguntas": ["¿Qué te hizo buscar apoyo justo ahora?",
                    "¿Has intentado algo antes para controlar tu peso? ¿Qué te funcionó y qué no?",
                    "Si en unos meses esto te sale bien, ¿qué cambiaría en tu día a día?"],
      "objeciones": ["Lo voy a pensar → Claro. ¿Qué te gustaría tener claro para decidir? Lo vemos ahorita "
                     "y si no te convence, no pasa nada.",
                     "¿Y si no me funciona? → Es justo lo que revisa el médico en tu primera consulta: "
                     "si el tratamiento es para ti y cómo se ajusta a tu caso."],
      "si_no_contesta": "Manda el WhatsApp de inmediato y vuelve a llamar en 15 a 20 minutos; si tampoco "
                        "contesta, un último intento entre 12:00 y 15:00."}),
    ({"lead_id": "EJEMPLO-2", "canal": "Referido", "anuncio": "(sin anuncio)", "objetivo": "diabetes tipo 2",
      "plan_de_interes": "2499", "estado": "CDMX", "edad": "58", "horas_esperando": 30.0,
      "prioridad": "media", "probabilidad": 0.05, "hora_actual": "09:00"},
     {"canal_recomendado": "whatsapp",
      "por_que_canal": "Lleva más de un día esperando: un WhatsApp con disculpa abre la puerta sin presionar.",
      "whatsapp": "Hola, soy tu asesor de Clivi; perdón por tardar en escribirte. Vi que te recomendaron "
                  "con nosotros para el control de la diabetes tipo 2. ¿Te queda mejor que platiquemos "
                  "por aquí o por llamada?",
      "guion_apertura": "Hola, te habla tu asesor de Clivi; te llamo porque alguien te recomendó con nosotros para el "
                        "control de la diabetes, y perdón por la demora. ¿Tienes unos minutos?",
      "preguntas": ["¿Quién te recomendó y qué te contó de su experiencia?",
                    "¿Cómo llevas hoy el control de tu diabetes y quién te da seguimiento?",
                    "¿Qué te gustaría que fuera distinto con tu tratamiento?"],
      "objeciones": ["Ya tengo doctor → Qué bueno. Clivi no lo sustituye: te acompaña entre consultas "
                     "y tu médico puede seguir siendo parte.",
                     "Está caro → Entiendo; el plan de $1,299 es una buena forma de empezar y "
                     "puedes cambiar después."],
      "si_no_contesta": "Espera respuesta al WhatsApp hasta la tarde; si no contesta, una llamada mañana "
                        "a media mañana y después solo un mensaje más."}),
]


def mensajes(lead: dict) -> list:
    """Sistema + ejemplos resueltos + el lead real."""
    m = [{"role": "system", "content": SISTEMA}]
    for ejemplo, respuesta in EJEMPLOS:
        m.append({"role": "user", "content": _contexto(ejemplo)})
        m.append({"role": "assistant", "content": json.dumps(respuesta, ensure_ascii=False)})
    m.append({"role": "user", "content": _contexto(lead)})
    return m


def plantilla(lead: dict) -> Contacto:
    """Versión sin IA, para cuando no hay credenciales o la API falla."""
    objetivo = lead.get("objetivo") or "tu salud"
    espera = lead.get("horas_esperando", 0)
    disculpa = "Perdón por tardar en escribirte. " if espera >= 12 else ""
    alta = lead.get("prioridad") == "alta"
    return Contacto(
        canal_recomendado="llamada" if alta else "whatsapp",
        por_que_canal="Es prioridad alta: vale la pena una llamada." if alta else "Un WhatsApp primero es menos invasivo.",
        whatsapp=f"¡Hola, soy tu asesor de Clivi y vi que te interesa el programa de {objetivo}! {disculpa}"
                 f"¿Te queda bien una llamada de 5 minutos hoy para contarte cómo funciona?",
        guion_apertura=f"Hola, te llamo de Clivi porque dejaste tus datos sobre {objetivo}. "
                       f"¿Tienes 5 minutos para que te cuente cómo funciona?",
        preguntas=["¿Qué te llevó a buscar ayuda en este momento?",
                   "¿Has intentado algo antes? ¿Qué funcionó y qué no?",
                   "¿Qué te gustaría lograr en los próximos 3 meses?"],
        objeciones=["Es caro → Puedes empezar con el plan de $1,299 y cambiar después.",
                    "No tengo tiempo → Es una clínica digital: todo es en línea, sin ir a un consultorio."],
        si_no_contesta="Manda el WhatsApp y reintenta la llamada entre 12:00 y 15:00, cuando más gente contesta.",
    )


def preparar_contacto(lead: dict, clave: str = "", client: openai.OpenAI | None = None,
                      modelo: str | None = None) -> tuple[Contacto, str]:
    """Devuelve (contacto, fuente) donde fuente es 'ia' o 'plantilla: <motivo>'."""
    clave = clave or clave_del_entorno()
    if client is None:
        if not clave:
            return plantilla(lead), "plantilla: falta la clave de API"
        client, modelo = crear_cliente(clave)
    modelo = modelo or MODELO_OPENAI
    try:
        r = client.chat.completions.parse(
            model=modelo,
            messages=mensajes(lead),
            response_format=Contacto,
            temperature=TEMPERATURA,
        )
        msg = r.choices[0].message
        if msg.refusal or msg.parsed is None:
            return plantilla(lead), "plantilla: la IA no devolvió una respuesta válida"
        return msg.parsed, "ia"
    except openai.AuthenticationError:
        return plantilla(lead), "plantilla: la clave de API no es válida"
    except openai.NotFoundError:
        return plantilla(lead), f"plantilla: el modelo {modelo} no está disponible en tu cuenta"
    except openai.RateLimitError:
        return plantilla(lead), "plantilla: límite de uso de la API, intenta en un minuto"
    except openai.APIStatusError as e:
        return plantilla(lead), f"plantilla: error de la API ({e.status_code})"
    except openai.APITimeoutError:
        return plantilla(lead), "plantilla: la IA tardó demasiado en responder"
    except openai.APIConnectionError:
        return plantilla(lead), "plantilla: sin conexión con la API"
    except (openai.OpenAIError, ValueError) as e:
        return plantilla(lead), f"plantilla: no se pudo leer la respuesta ({type(e).__name__})"
