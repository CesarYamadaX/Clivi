"""
Prueba el asistente con la IA real y revisa cada respuesta.

Uso (la clave se lee de .env o de la terminal):
    python probar_ia.py          # 12 leads
    python probar_ia.py 30       # 30 leads

Toma leads variados (prioridad alta, media y baja; recién llegados y de más de
12 h; peso y diabetes) de varias mañanas, le pide a la IA el primer contacto de
cada uno, revisa las reglas con primera_llamada/revision.py y escribe todo en
reporte_ia.md para leerlo con calma.
"""
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from primera_llamada.agente import clave_del_entorno, crear_cliente, preparar_contacto
from primera_llamada.modelo import leer_leads, lista_del_dia
from primera_llamada.revision import revisar

AQUI = Path(__file__).parent
MANANAS = [(datetime(2026, 11, 4), 9), (datetime(2026, 11, 2), 9), (datetime(2026, 10, 28), 9),
           (datetime(2026, 11, 9), 9), (datetime(2026, 11, 5), 15)]


def muestra(n: int) -> pd.DataFrame:
    leads, _ = leer_leads(AQUI / "data" / "leads_ficticios.csv")
    asesores = sorted(leads.asesor.dropna().unique())
    filas = []
    for dia, hora in MANANAS:
        lista, _ = lista_del_dia(leads, dia, hora, asesores)
        lista["hora_actual"] = f"{hora:02d}:00"
        filas.append(lista)
    todo = pd.concat(filas, ignore_index=True).drop_duplicates("lead_id")
    todo["grupo"] = (todo.prioridad + "-" + (todo.horas_esperando >= 12).map({True: "viejo", False: "nuevo"})
                     + "-" + todo.objetivo)
    # una ronda por grupo, luego otra, hasta juntar n
    todo["turno"] = todo.groupby("grupo").cumcount()
    return todo.sort_values(["turno", "probabilidad"], ascending=[True, False]).head(n)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    clave = clave_del_entorno()
    if not clave:
        sys.exit("Falta la clave: ponla en .env (copia .env.example) o corre  OPENROUTER_API_KEY=sk-or-... python probar_ia.py")
    _, modelo = crear_cliente(clave)
    print(f"Probando {n} leads con {modelo}…\n")

    lineas = [f"# Prueba del asistente con IA\n\n{datetime.now():%Y-%m-%d %H:%M} · modelo `{modelo}` · {n} leads\n"]
    resumen = []
    inicios, objeciones = set(), []
    for f in muestra(n).itertuples():
        lead = {k: getattr(f, k) for k in ["lead_id", "canal", "anuncio", "objetivo", "plan_de_interes", "estado",
                                            "edad", "horas_esperando", "prioridad", "probabilidad", "hora_actual"]}
        t = time.time()
        c, fuente = preparar_contacto(lead, clave)
        seg = time.time() - t
        problemas = revisar(c, lead) if fuente == "ia" else [fuente]
        ok = "✅" if not problemas else "⚠️"
        resumen.append((fuente == "ia", not problemas, seg))
        if fuente == "ia":
            inicios.add(" ".join(c.whatsapp.lower().replace(",", "").split()[:5]))
            objeciones += c.objeciones
        print(f"{ok} {lead['lead_id']} · {lead['prioridad']:5} · {lead['horas_esperando']:5.1f} h · "
              f"{lead['objetivo']:15} · {seg:4.1f} s · {'; '.join(problemas) or 'pasa'}")
        lineas += [
            f"\n## {ok} {lead['lead_id']} · prioridad {lead['prioridad']} · {lead['horas_esperando']:.1f} h esperando · "
            f"{lead['objetivo']} · {lead['canal']} · {lead['anuncio']}\n",
            f"*{fuente} · {seg:.1f} s*\n",
            f"**Empezar por:** {c.canal_recomendado}. {c.por_que_canal}\n",
            f"**WhatsApp:** {c.whatsapp}\n",
            f"**Llamada:** {c.guion_apertura}\n",
            "**Preguntas:**\n" + "\n".join(f"- {p}" for p in c.preguntas) + "\n",
            "**Objeciones:**\n" + "\n".join(f"- {o}" for o in c.objeciones) + "\n",
            f"**Si no contesta:** {c.si_no_contesta}\n",
            ("**Problemas:**\n" + "\n".join(f"- {p}" for p in problemas)) if problemas else "**Problemas:** ninguno",
        ]

    con_ia = sum(a for a, _, _ in resumen)
    pasan = sum(a and b for a, b, _ in resumen)
    tiempos = sorted(s for a, _, s in resumen if a) or [0]
    total = (f"\nRespondió la IA: {con_ia} de {len(resumen)} · pasan todas las reglas: {pasan} de {con_ia} · "
             f"tiempo típico {tiempos[len(tiempos) // 2]:.1f} s, máximo {tiempos[-1]:.1f} s")
    genericas = sum(bool(re.search(r"pensar|caro|no puedo hablar|no tengo tiempo", o, re.I)) for o in objeciones)
    total += (f"\nVariedad: {len(inicios)} formas distintas de empezar el WhatsApp en {con_ia} mensajes · "
              f"objeciones genéricas (pensarlo, caro, no puedo hablar): {genericas} de {len(objeciones)}")
    print(total)
    lineas.insert(1, total.strip() + "\n")
    (AQUI / "reporte_ia.md").write_text("\n".join(lineas), encoding="utf-8")
    print("Detalle completo en reporte_ia.md")


if __name__ == "__main__":
    main()
