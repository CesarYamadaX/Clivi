"""
Revisión automática de lo que escribe el asistente.

Revisa las reglas del mensaje (las mismas que le damos a la IA en agente.SISTEMA)
y devuelve una lista de problemas. Lista vacía = el mensaje pasa.
"""
import re
from typing import List

from .agente import Contacto

PRECIOS_VALIDOS = {"1,299", "1299", "1,599", "1599", "2,499", "2499", "4,299", "4299"}

# Promesas de resultados o consejos médicos que el asesor no puede hacer.
PROMESAS = re.compile(
    r"\b(\d+\s*(kg|kilos?)|bajar[aá]s?\s+\d+|garantiz\w*|te\s+cur\w*|cura(r|ción)?\b|"
    r"normaliz\w*\s+(tu\s+)?glucosa|resultados?\s+asegurad\w*|sin\s+falta)",
    re.IGNORECASE)

# Servicios concretos que el asistente no debe describir (lo explica el asesor).
SERVICIOS = re.compile(r"\b(nutri[oó]log\w*|endocrin\w*|psic[oó]log\w*|ozempic|wegovy|mounjaro|"
                       r"saxenda|semaglutida|tirzepatida|glp-?1|laboratorio)", re.IGNORECASE)

# Un saludo con nombre propio ("Hola Ana") inventa datos del lead.
SALUDO_CON_NOMBRE = re.compile(r"\b([Hh]ola|[Bb]uen[oa]s?\s+\w+)[,!\s]+(?!soy\b|te\b|qu[eé]\b|c[oó]mo\b)"
                               r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})\b")

DISCULPA = re.compile(r"perd[oó]n|disculp|demora|tard|esper", re.IGNORECASE)


def frases(texto: str) -> List[str]:
    return [f for f in re.split(r"(?<=[.!?])\s+", texto.strip()) if f]


def revisar(c: Contacto, lead: dict) -> List[str]:
    problemas = []
    wa = c.whatsapp.strip()
    if len(frases(wa)) > 3:
        problemas.append(f"WhatsApp con {len(frases(wa))} frases (máximo 3)")
    if not wa.endswith("?"):
        problemas.append("WhatsApp no termina en pregunta")
    if len(wa) > 400:
        problemas.append(f"WhatsApp muy largo ({len(wa)} caracteres)")
    if len(c.preguntas) != 3:
        problemas.append(f"{len(c.preguntas)} preguntas (se piden 3)")
    if len(c.objeciones) != 2:
        problemas.append(f"{len(c.objeciones)} objeciones (se piden 2)")

    todo = " ".join([c.por_que_canal, wa, c.guion_apertura, *c.preguntas, *c.objeciones, c.si_no_contesta])
    for m in PROMESAS.finditer(todo):
        problemas.append(f"posible promesa médica: «{m.group(0)}»")
    for m in SERVICIOS.finditer(todo):
        problemas.append(f"describe un servicio concreto: «{m.group(0)}»")
    for m in SALUDO_CON_NOMBRE.finditer(wa + " " + c.guion_apertura):
        if m.group(2).lower() not in {"clivi"}:
            problemas.append(f"posible nombre inventado: «{m.group(0)}»")
    for precio in re.findall(r"\$\s?([\d,]+)", todo):
        if precio.rstrip(",") not in PRECIOS_VALIDOS:
            problemas.append(f"precio que no existe: ${precio}")

    if lead.get("prioridad") == "alta" and c.canal_recomendado != "llamada":
        problemas.append("prioridad alta pero no recomienda llamada")
    if float(lead.get("horas_esperando") or 0) >= 12 and not DISCULPA.search(wa + " " + c.guion_apertura):
        problemas.append("lleva más de 12 h esperando y el mensaje no lo reconoce")
    objetivo = str(lead.get("objetivo") or "").lower()
    clave = "diabetes" if "diabetes" in objetivo else "peso" if "peso" in objetivo else ""
    if clave and clave not in (wa + " " + c.guion_apertura).lower():
        problemas.append(f"no menciona el objetivo del lead ({objetivo})")
    return problemas
