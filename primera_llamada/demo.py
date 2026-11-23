"""
Respuestas de la IA guardadas para la demo.

guardar_demo.py le pide a la IA el primer contacto de los leads de la demo y los
guarda en data/respuestas_demo.json. La app los muestra al instante, sin depender
de la red ni esperar a la IA. Si un lead no está guardado, se genera en vivo.
"""
import json
from pathlib import Path
from typing import Dict, Optional

from .agente import Contacto

ARCHIVO = Path(__file__).resolve().parents[1] / "data" / "respuestas_demo.json"


def llave(lead: dict) -> str:
    """El mismo lead a otra hora espera distinto y recibe otro mensaje, así que la hora entra en la llave."""
    return f"{lead['lead_id']}|{lead.get('hora_actual', '')}|{float(lead.get('horas_esperando') or 0):.2f}"


def cargar(ruta: Optional[Path] = None) -> Dict[str, Contacto]:
    ruta = ruta or ARCHIVO
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return {k: Contacto.model_validate(v) for k, v in datos.get("respuestas", {}).items()}
    except (OSError, ValueError):
        return {}


def respuesta_guardada(lead: dict, ruta: Optional[Path] = None) -> Optional[Contacto]:
    return cargar(ruta).get(llave(lead))
