"""
Primera Llamada · app en Streamlit.
Correr:  streamlit run app.py
"""
from datetime import timedelta
from html import escape
from pathlib import Path
from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st

from primera_llamada.agente import clave_del_entorno, preparar_contacto
from primera_llamada.modelo import leer_leads, lista_del_dia, validar

DATOS = Path(__file__).parent / "data" / "leads_ficticios.csv"
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
PRIORIDAD = {"alta": "🔴 Alta", "media": "🟠 Media", "baja": "⚪ Baja"}
RESULTADO = {"venta": "✅ Venta", "en_seguimiento": "🔁 En seguimiento", "no_contesta": "📵 No contestó",
             "no_interesado": "✖️ No interesado", "sin_contactar": "⏸️ Sin contactar"}

st.set_page_config(page_title="Primera Llamada", page_icon="📞", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 3.6rem; padding-bottom: 3rem; max-width: 1400px;}
[data-testid="stSidebar"] h3 {font-size: 0.95rem; margin-bottom: 0.2rem;}

.pl-hero {background: linear-gradient(120deg, #002d42 0%, #00547a 65%, #0a6d99 100%);
  color: #fff; border-radius: 18px; padding: 26px 30px 22px; margin-bottom: 18px;
  box-shadow: 0 6px 22px rgba(0,84,122,.20);}
.pl-hero .eyebrow {font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; opacity: .85; font-weight: 600;}
.pl-hero h1 {color: #fff; font-size: 2.3rem; margin: 4px 0 6px; padding: 0; line-height: 1.15;}
.pl-hero p {margin: 0 0 14px; opacity: .93; font-size: 1.02rem; max-width: 760px;}
.pl-chip {display: inline-block; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.28);
  border-radius: 999px; padding: 4px 12px; margin: 0 6px 6px 0; font-size: .86rem; font-weight: 500;}

.pl-kpi {background: #fff; border: 1px solid #e5eef2; border-radius: 14px; padding: 16px 18px; min-height: 128px;
  box-shadow: 0 1px 3px rgba(31,41,55,.05);}
.pl-kpi .label {font-size: .82rem; color: #65758b; font-weight: 600; text-transform: uppercase; letter-spacing: .04em;}
.pl-kpi .value {font-size: 2.1rem; font-weight: 700; color: #1f2937; line-height: 1.15; margin: 4px 0 2px;}
.pl-kpi .hint {font-size: .85rem; color: #65758b;}
.pl-kpi.accent {border-left: 5px solid #ef4444;}
.pl-kpi.good {border-left: 5px solid #00547a;}

.pl-card {background: #fff; border: 1px solid #e5eef2; border-radius: 14px; padding: 16px 18px; height: 100%;
  box-shadow: 0 1px 3px rgba(31,41,55,.05);}
.pl-card.top3 {min-height: 262px;}
.pl-card .top {display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;}
.pl-rank {background: #00547a; color: #fff; border-radius: 8px; padding: 2px 9px; font-weight: 700; font-size: .9rem;}
.pl-pill {border-radius: 999px; padding: 2px 10px; font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;}
.pl-pill.alta {background: #fde8e8; color: #b91c1c;}
.pl-pill.media {background: #fff1dc; color: #b45309;}
.pl-pill.baja {background: #f3f6f7; color: #65758b;}
.pl-card .prob {font-size: 1.9rem; font-weight: 700; color: #1f2937; line-height: 1.1;}
.pl-card .prob small {font-size: .85rem; font-weight: 500; color: #65758b;}
.pl-card .meta {font-size: .88rem; color: #65758b; margin: 6px 0 10px;}
.pl-card .meta b {color: #1f2937;}
.pl-card .why {font-size: .9rem; background: #e9f5fb; border-radius: 10px; padding: 10px 12px; color: #1f2937;}

.pl-section {font-size: 1.15rem; font-weight: 700; color: #1f2937; margin: 18px 0 8px;}
.pl-muted {color: #65758b; font-size: .9rem;}
.pl-facts {display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; margin: 8px 0 12px;}
.pl-facts div {font-size: .9rem; color: #65758b;}
.pl-facts b {display: block; color: #1f2937; font-size: .98rem;}
.pl-big {font-size: 2.6rem; font-weight: 800; line-height: 1;}
.pl-wa {background: #e7f8ee; border: 1px solid #b9e6cb; border-radius: 14px 14px 14px 4px; padding: 14px 16px;
  font-size: .98rem; color: #1f2937; white-space: pre-wrap;}
.pl-formula {background: #fff; font-weight: 600; line-height: 1.7; border: 1px dashed #9fc7da;
  border-radius: 12px; padding: 14px 16px; font-size: .95rem; color: #1f2937;}

.stTabs [data-baseweb="tab-list"] {gap: 6px;}
.stTabs [data-baseweb="tab"] {font-weight: 600; padding: 0 14px;}
.stTabs [data-baseweb="tab"] p {font-size: 1rem;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- utilidades
def fecha_txt(d) -> str:
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"


def horas_txt(h: float) -> str:
    if h < 1:
        return f"{max(1, round(h * 60))} min"
    return f"{h:.1f} h" if h < 24 else f"{round(h)} h"


def anuncio_txt(fila) -> str:
    return fila.canal if fila.anuncio == "(sin anuncio)" else f"{fila.canal} · {fila.anuncio}"


def kpi(col, etiqueta: str, valor: str, pista: str, clase: str = "") -> None:
    col.markdown(f'<div class="pl-kpi {clase}"><div class="label">{etiqueta}</div>'
                 f'<div class="value">{valor}</div><div class="hint">{pista}</div></div>', unsafe_allow_html=True)


def tarjeta_lead(col, fila, mostrar: bool) -> None:
    extra = ""
    if mostrar:
        extra = f'<div class="meta">Qué pasó: <b>{escape(RESULTADO.get(fila.resultado, str(fila.resultado)))}</b></div>'
    col.markdown(f"""
<div class="pl-card top3">
  <div class="top"><span class="pl-rank">#{fila.orden}</span><span class="pl-pill {fila.prioridad}">{fila.prioridad}</span></div>
  <div class="prob">{fila.probabilidad * 100:.1f}% <small>probabilidad de venta</small></div>
  <div class="meta"><b>{escape(str(fila.lead_id))}</b> · {escape(anuncio_txt(fila))}<br>
    Asignado a <b>{escape(str(fila.asignado))}</b> · esperando {horas_txt(fila.horas_esperando)}</div>
  <div class="why">💡 {escape(fila.razon)}</div>
  {extra}
</div>""", unsafe_allow_html=True)


def grafica_validacion(pct: dict) -> alt.LayerChart:
    datos = pd.DataFrame({
        "orden": ["Primera Llamada", "Orden real de los asesores", "Orden de llegada"],
        "pct": [pct["primera_llamada"], pct["orden_real"], pct["orden_llegada"]],
        "nuestro": [True, False, False],
    })
    y = alt.Y("orden:N", sort=None, title=None, axis=alt.Axis(labelFontSize=13, labelLimit=260))
    barras = alt.Chart(datos).mark_bar(cornerRadiusEnd=6, height=34).encode(
        x=alt.X("pct:Q", title="% de las ventas que quedan en el primer tercio", scale=alt.Scale(domain=[0, 100])),
        y=y,
        color=alt.condition(alt.datum.nuestro, alt.value("#00547a"), alt.value("#c6d6df")),
        tooltip=[alt.Tooltip("orden:N", title="Orden"), alt.Tooltip("pct:Q", title="%", format=".0f")],
    )
    texto = barras.mark_text(align="left", dx=6, fontSize=14, fontWeight="bold", color="#1f2937").encode(
        text=alt.Text("pct:Q", format=".0f"), color=alt.value("#1f2937"))
    azar = alt.Chart(pd.DataFrame({"x": [100 / 3]})).mark_rule(strokeDash=[5, 4], color="#ef4444", size=2).encode(x="x:Q")
    nota = alt.Chart(pd.DataFrame({"x": [100 / 3], "t": ["al azar: 33%"]})).mark_text(
        align="left", dx=5, dy=-8, color="#ef4444", fontSize=12).encode(x="x:Q", y=alt.value(0), text="t:N")
    return (barras + texto + azar + nota).properties(height=190)


@st.cache_data
def cargar(contenido: Optional[bytes]):
    if contenido is None:
        return leer_leads(DATOS)
    from io import BytesIO
    return leer_leads(BytesIO(contenido))


@st.cache_data
def validacion(contenido: Optional[bytes]):
    leads, _ = cargar(contenido)
    return validar(leads)


# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.markdown("## 📞 Primera Llamada")
    st.caption("Lista diaria de llamadas para el equipo de ventas.")

    with st.expander("📁 Datos", expanded=False):
        archivo = st.file_uploader("Cargar otro CSV (mismo formato que leads_ficticios.csv)", type="csv")
    contenido = archivo.getvalue() if archivo else None
    try:
        leads, resumen = cargar(contenido)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    st.markdown("### 🗓️ ¿Cuándo?")
    primero = leads.reg.min().normalize() + timedelta(days=7)
    ultimo = leads.reg.max().normalize() + timedelta(days=1)
    dias = {fecha_txt(d) + (" · mañana siguiente a los datos" if d == ultimo else ""): d
            for d in pd.date_range(primero, ultimo)[::-1]}
    dia = dias[st.selectbox("Día", list(dias))]
    hora = st.select_slider("Hora", options=list(range(7, 21)), value=9, format_func=lambda h: f"{h:02d}:00")

    st.markdown("### 👥 ¿Quién trabaja hoy?")
    todos = sorted(leads.asesor.dropna().unique()) if "asesor" in leads else []
    asesores = st.multiselect("Asesores", todos, default=todos, label_visibility="collapsed")

    st.markdown("### 🔍 Validación")
    mostrar = st.toggle("Mostrar qué pasó después", help="Revela el resultado real de cada lead para comprobar el orden.")

    st.markdown("### 🤖 Asistente con IA")
    clave = st.text_input("Clave de API (OpenRouter u OpenAI)", type="password",
                          help="Opcional. Sin clave, el asistente usa una plantilla fija. "
                               "También lee OPENROUTER_API_KEY u OPENAI_API_KEY del entorno o de los secretos de Streamlit.")
    if not clave:
        try:
            clave = st.secrets.get("OPENROUTER_API_KEY", "") or st.secrets.get("OPENAI_API_KEY", "")
        except Exception:
            clave = ""
    clave = clave or clave_del_entorno()
    if clave:
        st.success("IA activa · GPT-6 Luna", icon="✅")
    else:
        st.info("Sin clave: el asistente usará una plantilla.", icon="ℹ️")

    st.divider()
    st.caption(f"{resumen['registros']:,} registros leídos · {resumen['duplicados']} teléfonos repetidos quitados · "
               f"{resumen['fechas_ddmm']} fechas DD/MM corregidas · {resumen['personas']:,} personas únicas.")

# ---------------------------------------------------------------- cálculo
lista, modelo = lista_del_dia(leads, dia.to_pydatetime(), hora, asesores)
n = len(lista)
tercio = -(-n // 3) if n else 0
esperadas = float(lista.probabilidad.sum()) if n else 0.0
concentracion = float(lista.probabilidad.iloc[:tercio].sum()) / esperadas if esperadas else 0.0
urgentes = int((lista.horas_esperando < 0.25).sum()) if n else 0

# ---------------------------------------------------------------- encabezado
estado_ia = "🤖 IA activa" if clave else "🤖 Plantilla (sin IA)"
st.markdown(f"""
<div class="pl-hero">
  <div class="eyebrow">Clivi · Misión A</div>
  <h1>Primera Llamada</h1>
  <p>A quién llama primero cada asesor esta mañana, ordenado por la probabilidad de venta si se le llama ahora.</p>
  <span class="pl-chip">📅 {fecha_txt(dia).capitalize()} · {hora:02d}:00</span>
  <span class="pl-chip">👥 {len(asesores)} asesor{'es' if len(asesores) != 1 else ''}</span>
  <span class="pl-chip">{estado_ia}</span>
  {'<span class="pl-chip">🔍 Modo validación</span>' if mostrar else ''}
</div>""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
kpi(k1, "Leads en cola", f"{n}", "sin primera llamada, últimas 48 h")
kpi(k2, "Prioridad alta", f"{int((lista.prioridad == 'alta').sum()) if n else 0}",
    f"probabilidad ≥ 8% · {urgentes} llegaron hace < 15 min", "accent")
kpi(k3, "Ventas esperadas", f"{esperadas:.1f}", "si se llama a toda la cola ahora")
kpi(k4, "Primer tercio", f"{concentracion:.0%}" if n else "–",
    f"de las ventas esperadas están en los primeros {tercio}", "good")

st.write("")
tab_lista, tab_contacto, tab_modelo = st.tabs(["📋  Lista del día", "💬  Preparar contacto", "📊  Cómo decide y si funciona"])

# ---------------------------------------------------------------- 1. lista
with tab_lista:
    if lista.empty:
        st.info("No hay leads esperando primera llamada a esta hora. Prueba las 9:00 o elige otro día.", icon="☕")
    else:
        st.markdown('<div class="pl-section">🎯 Llamar primero</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for col, fila in zip(cols, lista.head(3).itertuples()):
            tarjeta_lead(col, fila, mostrar)

        st.markdown('<div class="pl-section">📋 Lista completa por asesor</div>', unsafe_allow_html=True)
        if not asesores:
            st.warning("Elige al menos un asesor en la barra lateral para repartir la lista.", icon="👥")
        etiquetas = [f"Todos · {n}"] + [f"{a} · {(lista.asignado == a).sum()}" for a in asesores]
        grupos = [lista] + [lista[lista.asignado == a] for a in asesores]
        for i, (pestaña, g) in enumerate(zip(st.tabs(etiquetas), grupos)):
            with pestaña:
                if g.empty:
                    st.info("Este asesor no tiene leads asignados a esta hora.")
                    continue
                altas = int((g.prioridad == "alta").sum())
                st.markdown(f'<div class="pl-muted">{len(g)} leads · {altas} de prioridad alta · '
                            f'{g.probabilidad.sum():.1f} ventas esperadas. Marca ✓ al llamar.</div>',
                            unsafe_allow_html=True)
                if mostrar:
                    k = -(-len(g) // 3)
                    tot, top = int(g.venta.sum()), int(g.venta.iloc[:k].sum())
                    if tot:
                        st.success(f"En esta lista hubo **{tot} venta{'s' if tot > 1 else ''}**. "
                                   f"**{top}** {'quedó' if top == 1 else 'quedaron'} en el primer tercio (los primeros {k}).",
                                   icon="✅")
                    else:
                        st.warning("Ninguno de estos leads terminó comprando. Prueba miércoles 4 nov o lunes 2 nov.")
                tabla = pd.DataFrame({
                    "#": g.orden.to_numpy(),
                    "llamado": False,
                    "prioridad": g.prioridad.map(PRIORIDAD).to_numpy(),
                    "probabilidad": (g.probabilidad * 100).to_numpy(),
                    "lead": g.lead_id.to_numpy(),
                    "asesor": g.asignado.to_numpy(),
                    "teléfono": g.telefono.to_numpy(),
                    "esperando": [horas_txt(h) for h in g.horas_esperando],
                    "por qué este lugar": g.razon.to_numpy(),
                    "origen": [anuncio_txt(f) for f in g.itertuples()],
                })
                if i > 0:
                    tabla = tabla.drop(columns="asesor")
                if mostrar:
                    tabla["qué pasó"] = g.resultado.map(lambda r: RESULTADO.get(r, r)).to_numpy()
                st.data_editor(
                    tabla, hide_index=True, width="stretch",
                    height=min(35 * (len(tabla) + 1) + 3, 640),
                    disabled=[c for c in tabla.columns if c != "llamado"],
                    key=f"tabla-{dia:%Y%m%d}-{hora}-{i}",
                    column_config={
                        "#": st.column_config.NumberColumn("#", width="small"),
                        "llamado": st.column_config.CheckboxColumn("✓", width="small"),
                        "prioridad": st.column_config.TextColumn("Prioridad", width="small"),
                        "probabilidad": st.column_config.ProgressColumn("Probabilidad", format="%.1f%%",
                                                                        min_value=0, max_value=25, width="medium"),
                        "lead": st.column_config.TextColumn("Lead", width="small"),
                        "asesor": st.column_config.TextColumn("Asesor", width="small"),
                        "origen": st.column_config.TextColumn("Canal · anuncio", width="medium"),
                        "esperando": st.column_config.TextColumn("Esperando", width="small"),
                        "teléfono": st.column_config.TextColumn("Teléfono", width="small"),
                        "por qué este lugar": st.column_config.TextColumn("Por qué este lugar", width="large"),
                        "qué pasó": st.column_config.TextColumn("Qué pasó", width="small"),
                    },
                )

# ---------------------------------------------------------------- 2. asistente
with tab_contacto:
    st.markdown('<div class="pl-muted">El asistente decide si empezar por llamada o WhatsApp, escribe el mensaje, '
                'el guion y qué hacer si no contesta. Usa solo lo que sabemos del lead.</div>', unsafe_allow_html=True)
    if lista.empty:
        st.info("No hay leads en la lista a esta hora.")
    else:
        izq, der = st.columns([1, 1.5], gap="large")
        with izq:
            elegido = st.selectbox(
                "Lead", lista.index,
                format_func=lambda i: f"#{lista.at[i, 'orden']} · {lista.at[i, 'lead_id']} · "
                                      f"{lista.at[i, 'prioridad']} · {lista.at[i, 'asignado']}")
            fila = lista.loc[elegido]
            edad = fila.get("edad")
            st.markdown(f"""
<div class="pl-card">
  <div class="top"><span class="pl-rank">#{fila.orden}</span><span class="pl-pill {fila.prioridad}">{fila.prioridad}</span></div>
  <div class="prob">{fila.probabilidad * 100:.1f}% <small>probabilidad de venta</small></div>
  <div class="pl-facts">
    <div>Objetivo<b>{escape(str(fila.get("objetivo", "–")))}</b></div>
    <div>Plan de interés<b>${escape(str(fila.get("plan_de_interes", "–")))} MXN</b></div>
    <div>Origen<b>{escape(anuncio_txt(fila))}</b></div>
    <div>Esperando<b>{horas_txt(fila.horas_esperando)}</b></div>
    <div>Estado · edad<b>{escape(str(fila.get("estado", "–")))} · {escape(str(edad)) if pd.notna(edad) else "–"}</b></div>
    <div>Asesor<b>{escape(str(fila.asignado))}</b></div>
  </div>
  <div class="why">💡 {escape(fila.razon)}</div>
</div>""", unsafe_allow_html=True)
            st.write("")
            if st.button("✨ Preparar contacto", type="primary", width="stretch"):
                lead = {k: fila.get(k) for k in ["lead_id", "canal", "anuncio", "objetivo", "plan_de_interes", "estado",
                                                 "edad", "horas_esperando", "prioridad", "probabilidad"]}
                lead["hora_actual"] = f"{hora:02d}:00"
                with st.spinner("Preparando el primer contacto…"):
                    contacto, fuente = preparar_contacto(lead, clave)
                st.session_state["contacto"] = (fila.lead_id, contacto, fuente)

        with der:
            guardado = st.session_state.get("contacto")
            if not guardado or guardado[0] != fila.lead_id:
                st.markdown('<div class="pl-card" style="text-align:center; padding:48px 24px;">'
                            '<div style="font-size:2.4rem">💬</div>'
                            '<div class="pl-section" style="margin-top:6px">Elige un lead y presiona “Preparar contacto”</div>'
                            '<div class="pl-muted">Verás el canal recomendado, el WhatsApp listo para enviar, '
                            'el guion de llamada y las objeciones probables.</div></div>', unsafe_allow_html=True)
            else:
                lid, c, fuente = guardado
                icono = "📞" if c.canal_recomendado == "llamada" else "💬"
                st.success(f"{icono} **Empezar por {c.canal_recomendado}.** {c.por_que_canal}")
                st.caption("✨ Escrito con IA (GPT-6 Luna)" if fuente == "ia" else f"📝 Usando {fuente}")
                with st.container(border=True):
                    st.markdown("**💬 WhatsApp listo para enviar**")
                    st.markdown(f'<div class="pl-wa">{escape(c.whatsapp)}</div>', unsafe_allow_html=True)
                    with st.expander("Copiar texto"):
                        st.code(c.whatsapp, language=None, wrap_lines=True)
                a, b = st.columns(2)
                with a, st.container(border=True):
                    st.markdown("**📞 Guion de llamada**")
                    st.write(c.guion_apertura)
                    st.markdown("**Preguntas para entender su caso**")
                    st.markdown("\n".join(f"{j}. {p}" for j, p in enumerate(c.preguntas, 1)))
                with b, st.container(border=True):
                    st.markdown("**🛡️ Objeciones probables**")
                    st.markdown("\n".join(f"- {o}" for o in c.objeciones))
                    st.markdown("**⏰ Si no contesta**")
                    st.write(c.si_no_contesta)

# ---------------------------------------------------------------- 3. modelo y validación
with tab_modelo:
    v = validacion(contenido)
    if v["ventas"]:
        pct = {k: 100 * v[k] / v["ventas"] for k in ("primera_llamada", "orden_real", "orden_llegada")}
        st.markdown('<div class="pl-section">¿Funciona? Ventas que quedan en el primer tercio de la lista de las 9:00</div>',
                    unsafe_allow_html=True)
        a, b, c = st.columns(3)
        kpi(a, "Primera Llamada", f"{pct['primera_llamada']:.0f}%",
            f"{v['primera_llamada']} de {v['ventas']} ventas en el primer tercio", "good")
        kpi(b, "Orden real de los asesores", f"{pct['orden_real']:.0f}%", f"{v['orden_real']} de {v['ventas']} ventas")
        kpi(c, "Orden de llegada", f"{pct['orden_llegada']:.0f}%", f"{v['orden_llegada']} de {v['ventas']} ventas")
        st.altair_chart(grafica_validacion(pct), use_container_width=True)
        st.caption(f"{v['mananas']} mañanas, {v['leads']} leads en cola, {v['ventas']} ventas. "
                   f"Cada día el modelo solo aprende de días anteriores. Un tercio al azar daría 33%.")

    st.markdown('<div class="pl-section">Cómo decide el orden</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1, 1, 1.5], gap="large")
    with f1:
        st.markdown('<div class="pl-formula">probabilidad =<br>&nbsp;&nbsp;tasa de venta del anuncio<br>'
                    '&nbsp;&nbsp;× efecto del tiempo esperando</div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("- **Aprende solo del pasado:** cada día usa únicamente los días anteriores.\n"
                    "- **Anuncios con pocos datos** se acercan al promedio de su canal.\n"
                    "- **Reparto en serpiente** (A B C C B A…) para que todos reciban leads buenos.\n"
                    "- Prioridad **alta** ≥ 8%, **media** ≥ 3%, **baja** el resto.")
    with f2:
        st.markdown("**⏱️ Efecto del tiempo esperando**")
        st.dataframe(modelo.tabla_efecto(), hide_index=True, width="stretch",
                     column_config={"si se le llama": st.column_config.TextColumn("Si se le llama"),
                                    "efecto": st.column_config.NumberColumn("Efecto", format="×%.2f")})
        st.caption("Llamar en los primeros 15 minutos multiplica la probabilidad; después de 12 h cae a menos de la mitad.")
    with f3:
        st.markdown("**📣 Tasa de venta por anuncio**")
        st.dataframe(modelo.tabla_anuncios().assign(tasa_venta=lambda t: t.tasa_venta * 100), hide_index=True,
                     width="stretch", height=260,
                     column_config={"canal": st.column_config.TextColumn("Canal", width="small"),
                                    "anuncio": st.column_config.TextColumn("Anuncio", width="medium"),
                                    "leads": st.column_config.NumberColumn("Leads", width="small"),
                                    "tasa_venta": st.column_config.ProgressColumn("Venta", format="%.1f%%", width="medium",
                                                                                  min_value=0, max_value=20)})
