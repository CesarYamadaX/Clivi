"""Corre la validación desde la terminal:  python validar.py [ruta.csv]"""
import sys

from primera_llamada.modelo import leer_leads, validar

ruta = sys.argv[1] if len(sys.argv) > 1 else "data/leads_ficticios.csv"
leads, resumen = leer_leads(ruta)
print("Limpieza:", resumen)
v = validar(leads)
print(f"{v['mananas']} mañanas, {v['leads']} leads en cola de las 9:00, {v['ventas']} ventas")
for k, nombre in [("primera_llamada", "Primera Llamada"), ("orden_real", "Orden real"), ("orden_llegada", "Orden de llegada")]:
    print(f"  {nombre:<16} {v[k]:>3} de {v['ventas']} ventas en el primer tercio ({100 * v[k] / v['ventas']:.0f}%)")
