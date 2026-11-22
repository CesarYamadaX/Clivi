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

import os

import openai
from pydantic import BaseModel, Field

OPENROUTER_URL = "https://openrouter.ai/api/v1"
MODELO_OPENROUTER = "openai/gpt-6-luna"
MODELO_OPENAI = "gpt-6-luna"
TIEMPO_MAXIMO = 45  # segundos; en una demo es mejor caer a la plantilla que dejar la pantalla congelada


def crear_cliente(clave: str) -> tuple[openai.OpenAI, str]:
    """Una clave sk-or-... va a OpenRouter; cualquier otra, directo a OpenAI."""
    if clave.startswith("sk-or-"):
        cliente = openai.OpenAI(api_key=clave, base_url=OPENROUTER_URL, timeout=TIEMPO_MAXIMO, max_retries=1,
                                default_headers={"X-Title": "Primera Llamada"})
        return cliente, os.environ.get("MODELO_IA", MODELO_OPENROUTER)
    return (openai.OpenAI(api_key=clave, timeout=TIEMPO_MAXIMO, max_retries=1),
            os.environ.get("MODELO_IA", MODELO_OPENAI))


def clave_del_entorno() -> str:
    return os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""

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
- La apertura de la llamada termina con una pregunta."""


class Contacto(BaseModel):
    canal_recomendado: Literal["llamada", "whatsapp"] = Field(
        description="Por dónde empezar. Llamada si es prioridad alta y está en horario; si no, WhatsApp.")
    por_que_canal: str = Field(description="Una frase que explica la elección.")
    whatsapp: str = Field(description="Mensaje listo para enviar, máximo 3 frases.")
    guion_apertura: str = Field(description="Primeras 2 frases de la llamada.")
    preguntas: list[str] = Field(description="3 preguntas para entender su caso.")
    objeciones: list[str] = Field(description="2 objeciones probables, cada una con una respuesta corta: 'objeción → respuesta'.")
    si_no_contesta: str = Field(description="Qué hacer y cuándo reintentar si no contesta.")


def _contexto(lead: dict) -> str:
    anuncio = lead.get("anuncio") or "(sin anuncio)"
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
    )


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
            messages=[{"role": "system", "content": SISTEMA},
                      {"role": "user", "content": _contexto(lead)}],
            response_format=Contacto,
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
