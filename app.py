"""
Primera Llamada · app en Streamlit.
Correr:  streamlit run app.py
"""
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st



from primera_llamada.agente import clave_del_entorno, preparar_contacto
from primera_llamada.modelo import leer_leads, lista_del_dia, validar

DATOS = Path(__file__).parent / "data" / "leads_ficticios.csv"
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
COLOR = {"alta": "🔴 alta", "media": "🟠 media", "baja": "⚪ baja"}

st.set_page_config(page_title="Primera Llamada", page_icon="📞", layout="wide")


def fecha_txt(d) -> str:
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"


@st.cache_data
def cargar(contenido: bytes | None):
    if contenido is None:
        return leer_leads(DATOS)
    from io import BytesIO
    return leer_leads(BytesIO(contenido))


@st.cache_data
def validacion(contenido: bytes | None):
    leads, _ = cargar(contenido)
    return validar(leads)


# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.header("Controles")
    archivo = st.file_uploader("Cargar mi CSV (mismo formato que leads_ficticios.csv)", type="csv")
    contenido = archivo.getvalue() if archivo else None
    try:
        leads, resumen = cargar(contenido)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    st.caption(f"{resumen['registros']:,} registros leídos · {resumen['duplicados']} teléfonos repetidos quitados · "
               f"{resumen['fechas_ddmm']} fechas DD/MM corregidas · {resumen['personas']:,} personas únicas.")

    primero = leads.reg.min().normalize() + timedelta(days=7)
    ultimo = leads.reg.max().normalize() + timedelta(days=1)
    dias = list(pd.date_range(primero, ultimo))[::-1]
    dia = st.selectbox("Día", dias, format_func=lambda d: fecha_txt(d) + (" (día siguiente a los datos)" if d == ultimo else ""))
    hora = st.select_slider("Hora", options=list(range(7, 21)), value=9, format_func=lambda h: f"{h:02d}:00")
    todos = sorted(leads.asesor.dropna().unique()) if "asesor" in leads else []
    asesores = st.multiselect("¿Quién trabaja hoy?", todos, default=todos)
    mostrar = st.toggle("Mostrar qué pasó después (validación)")

    st.divider()
    st.subheader("Asistente de seguimiento (IA)")
    clave = st.text_input("Clave de API (OpenRouter u OpenAI)", type="password",
                          help="Opcional. Sin clave, el asistente usa una plantilla fija. "
                               "También lee OPENROUTER_API_KEY u OPENAI_API_KEY del entorno o de los secretos de Streamlit.")
    if not clave:
        try:
            clave = st.secrets.get("OPENROUTER_API_KEY", "") or st.secrets.get("OPENAI_API_KEY", "")
        except Exception:
            clave = ""
    clave = clave or clave_del_entorno()
    st.caption("IA activa ✓" if clave else "Sin clave: se usará la plantilla.")

# ---------------------------------------------------------------- lista del día
lista, modelo = lista_del_dia(leads, dia.to_pydatetime(), hora, asesores)

st.caption("CLIVI · MISIÓN A")
st.title("Primera Llamada")
st.write("La lista de cada mañana: a quién llama primero cada asesor, ordenada por la probabilidad de venta si se le llama ahora.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads esperando primera llamada", len(lista))
c2.metric("Prioridad alta (≥ 8%)", int((lista.prioridad == "alta").sum()))
c3.metric("Ventas esperadas si se llama a todos ya", f"{lista.probabilidad.sum():.1f}")
c4.metric("Duplicados que no se volverán a llamar", resumen["duplicados"])

izq, der = st.columns([2.2, 1])

with izq:
    pestañas = st.tabs([f"Todos ({len(lista)})"] + [f"{a} ({(lista.asignado == a).sum()})" for a in asesores])
    grupos = [lista] + [lista[lista.asignado == a] for a in asesores]
    for i, (pestaña, g) in enumerate(zip(pestañas, grupos)):
        with pestaña:
            st.subheader(f"{fecha_txt(dia)}, {hora:02d}:00")
            if g.empty:
                st.info("No hay leads esperando primera llamada a esta hora. Prueba las 9:00 o otro día.")
                continue
            if mostrar:
                k = -(-len(g) // 3)
                tot, top = int(g.venta.sum()), int(g.venta.iloc[:k].sum())
                if tot:
                    st.success(f"En esta lista hubo {tot} venta{'s' if tot > 1 else ''}. "
                               f"{top} {'quedó' if top == 1 else 'quedaron'} en el primer tercio (los primeros {k}).")
                else:
                    st.warning("Ninguno de estos leads terminó comprando. Prueba miércoles 4 nov o lunes 2 nov.")
            tabla = pd.DataFrame({
                "#": range(1, len(g) + 1),
                "llamado": False,
                "lead": g.lead_id,
                "prioridad": g.prioridad.map(COLOR),
                "probabilidad": g.probabilidad * 100,
                "asesor": g.asignado,
                "canal · anuncio": g.canal + " · " + g.anuncio,
                "teléfono": g.telefono,
                "llegó": g.reg.dt.strftime("%d/%m %H:%M"),
                "por qué": g.razon,
            })
            if mostrar:
                tabla["qué pasó"] = g.resultado.str.replace("_", " ").to_numpy()
            st.data_editor(
                tabla, hide_index=True, width="stretch", height=min(36 * (len(tabla) + 1) + 3, 900), disabled=[c for c in tabla.columns if c != "llamado"],
                key=f"tabla-{dia:%Y%m%d}-{hora}-{i}",
                column_config={
                    "probabilidad": st.column_config.ProgressColumn("probabilidad", format="%.1f%%", min_value=0, max_value=25),
                    "por qué": st.column_config.TextColumn(width="large"),
                    "llamado": st.column_config.CheckboxColumn("✓"),
                },
            )

    # ------------------------------------------------------------ asistente
    st.divider()
    st.subheader("Preparar el primer contacto")
    st.caption("El asistente decide si empezar por llamada o WhatsApp y escribe el mensaje, el guion y qué hacer si no contesta.")
    if lista.empty:
        st.info("No hay leads en la lista.")
    else:
        opciones = lista.head(15)
        elegido = st.selectbox(
            "Lead", opciones.index,
            format_func=lambda i: f"#{i + 1} · {opciones.at[i, 'lead_id']} · {opciones.at[i, 'prioridad']} · "
                                  f"{opciones.at[i, 'canal']} · {opciones.at[i, 'asignado']}")
        if st.button("Preparar contacto", type="primary"):
            fila = lista.loc[elegido]
            lead = {k: fila.get(k) for k in ["lead_id", "canal", "anuncio", "objetivo", "plan_de_interes", "estado",
                                             "edad", "horas_esperando", "prioridad", "probabilidad"]}
            lead["hora_actual"] = f"{hora:02d}:00"
            with st.spinner("Preparando…"):
                contacto, fuente = preparar_contacto(lead, clave)
            st.session_state["contacto"] = (fila.lead_id, contacto, fuente)
        if "contacto" in st.session_state:
            lid, c, fuente = st.session_state["contacto"]
            st.markdown(f"**{lid}** · empezar por **{c.canal_recomendado}**. {c.por_que_canal}")
            st.caption("Escrito con IA (GPT-6 Luna)" if fuente == "ia" else f"Usando {fuente}")
            a, b = st.columns(2)
            with a:
                st.markdown("**WhatsApp**")
                st.code(c.whatsapp, language=None, wrap_lines=True)
                st.markdown("**Si no contesta**")
                st.write(c.si_no_contesta)
            with b:
                st.markdown("**Guion de llamada**")
                st.write(c.guion_apertura)
                st.markdown("\n".join(f"- {p}" for p in c.preguntas))
                st.markdown("**Objeciones probables**")
                st.markdown("\n".join(f"- {o}" for o in c.objeciones))

with der:
    st.subheader("Cómo decide el orden")
    st.code("probabilidad =\n  tasa de venta del anuncio\n  × efecto del tiempo esperando", language=None)
    st.caption("Aprende solo de los días anteriores al que eliges. Los anuncios con pocos datos se acercan al promedio de su canal.")
    st.markdown("**Efecto del tiempo esperando**")
    st.dataframe(modelo.tabla_efecto(), hide_index=True, width="stretch",
                 column_config={"efecto": st.column_config.NumberColumn(format="×%.2f")})
    st.markdown("**Tasa de venta por anuncio**")
    st.dataframe(modelo.tabla_anuncios().assign(tasa_venta=lambda t: t.tasa_venta * 100), hide_index=True, width="stretch",
                 column_config={"tasa_venta": st.column_config.NumberColumn("venta", format="%.1f%%")})

    st.subheader("¿Funciona?")
    v = validacion(contenido)
    if v["ventas"]:
        st.markdown("Ventas que quedan en el primer tercio de la lista de las 9:00")
        res = pd.DataFrame({
            "orden": ["Primera Llamada", "Orden real de los asesores", "Orden de llegada"],
            "% de ventas": [100 * v[k] / v["ventas"] for k in ("primera_llamada", "orden_real", "orden_llegada")],
        })
        st.bar_chart(res, x="orden", y="% de ventas", horizontal=True, color="#0f6e5c")
        st.caption(f"{v['mananas']} mañanas, {v['leads']} leads en cola, {v['ventas']} ventas. "
                   f"Cada día el modelo solo usa datos de días anteriores. Un tercio al azar daría 33%.")
