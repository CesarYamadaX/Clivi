"""
Guarda las respuestas de la IA para la demo (para que no dependa de la red).

Uso (la clave se lee de .env):
    python guardar_demo.py

Genera el primer contacto de todos los leads de la lista que abre la app por
defecto (la mañana siguiente a los datos, 9:00, todos los asesores), revisa cada
uno con revision.py y guarda solo los que escribió la IA en data/respuestas_demo.json.
"""
import json
import sys
import time
from datetime import datetime

import pandas as pd

from primera_llamada.agente import clave_del_entorno, crear_cliente, preparar_contacto
from primera_llamada.demo import ARCHIVO, llave
from primera_llamada.modelo import leer_leads, lista_del_dia
from primera_llamada.revision import revisar
from probar_ia import AQUI

CAMPOS = ["lead_id", "canal", "anuncio", "objetivo", "plan_de_interes", "estado",
          "edad", "horas_esperando", "prioridad", "probabilidad"]
HORAS = [9]


def leads_demo():
    leads, _ = leer_leads(AQUI / "data" / "leads_ficticios.csv")
    dia = leads.reg.max().normalize() + pd.Timedelta(days=1)
    asesores = sorted(leads.asesor.dropna().unique())
    for hora in HORAS:
        lista, _ = lista_del_dia(leads, dia.to_pydatetime(), hora, asesores)
        for _, fila in lista.iterrows():
            lead = {k: fila.get(k) for k in CAMPOS}
            lead["hora_actual"] = f"{hora:02d}:00"
            yield lead


def main():
    clave = clave_del_entorno()
    if not clave:
        sys.exit("Falta la clave: ponla en .env (copia .env.example).")
    _, modelo = crear_cliente(clave)
    respuestas, fallas = {}, []
    for lead in leads_demo():
        t = time.time()
        c, fuente = preparar_contacto(lead, clave)
        if not fuente.startswith("ia"):
            fallas.append(f"{lead['lead_id']}: {fuente}")
            print(f"✖️ {lead['lead_id']} · {fuente}")
            continue
        problemas = revisar(c, lead)
        respuestas[llave(lead)] = c.model_dump()
        print(f"{'✅' if not problemas else '⚠️'} {lead['lead_id']} · {time.time() - t:4.1f} s · "
              f"{'; '.join(problemas) or 'pasa'}")
    ARCHIVO.write_text(json.dumps({"modelo": modelo, "generado": f"{datetime.now():%Y-%m-%d %H:%M}",
                                   "respuestas": respuestas}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGuardadas {len(respuestas)} respuestas en {ARCHIVO.name}" + (f" · {len(fallas)} fallaron" if fallas else ""))


if __name__ == "__main__":
    main()
