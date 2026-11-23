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
from primera_llamada.demo import ARCHIVO as RESPUESTAS_DEMO, respuesta_guardada
from primera_llamada import registro
from primera_llamada.modelo import leer_leads, lista_del_dia, validar

DATOS = Path(__file__).parent / "data" / "leads_ficticios.csv"
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
PRIORIDAD = {"alta": "🔴 Alta", "media": "🟠 Media", "baja": "⚪ Baja"}
RESULTADO = {"venta": "Venta", "en_seguimiento": "En seguimiento", "no_contesta": "No contestó",
             "no_interesado": "No interesado", "sin_contactar": "Sin contactar"}

st.set_page_config(page_title="Primera Llamada", page_icon="📞", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');
/* Mesa de trabajo de un asesor: encabezado sobrio, una franja de cifras, tarjetas de lead sin adornos.
   Tinta petróleo + azul Clivi; grises con un toque azul; rojo y ámbar solo para prioridad. */
:root {
  --pl-ink: #0e2a36;      /* texto principal */
  --pl-brand: #00547a;    /* azul Clivi */
  --pl-muted: #5a6e78;    /* texto secundario */
  --pl-line: #dbe6ea;     /* filetes y bordes */
  --pl-surface: #ffffff;  /* tarjetas */
  --pl-wash: #eef4f6;     /* fondos suaves */
  --pl-alta: #b4232a; --pl-alta-bg: #fbeceb;
  --pl-media: #9a5b0f; --pl-media-bg: #fbf1e2;
  --pl-display: 'Manrope', 'Inter', system-ui, sans-serif;
}
.block-container {padding-top: 3.2rem; padding-bottom: 4rem; max-width: 1320px;}
.block-container, .pl-num {font-variant-numeric: tabular-nums;}

/* barra lateral */
[data-testid="stSidebar"] h2 {font-family: var(--pl-display); font-size: 1.15rem; font-weight: 700;
  letter-spacing: -.01em; color: var(--pl-ink);}
[data-testid="stSidebar"] h3 {font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .09em;
  color: var(--pl-muted); margin: 1.1rem 0 .1rem; padding-top: 1rem; border-top: 1px solid var(--pl-line);}

/* encabezado */
.pl-hero {display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; flex-wrap: wrap;
  padding: 0 0 20px; margin-bottom: 22px; border-bottom: 1px solid var(--pl-line);}
.pl-hero .marca {font-size: .8rem; font-weight: 600; color: var(--pl-brand); letter-spacing: .02em; margin-bottom: 6px;}
.pl-hero h1 {font-family: var(--pl-display); color: var(--pl-ink); font-size: 2.5rem; font-weight: 800;
  letter-spacing: -.035em; margin: 0; padding: 0; line-height: 1.05;}
.pl-hero p {margin: 8px 0 0; color: var(--pl-muted); font-size: 1rem; max-width: 620px; text-wrap: balance;}
.pl-hero .estado {text-align: right; color: var(--pl-muted); font-size: .88rem; line-height: 1.6;}
.pl-hero .estado b {display: block; font-family: var(--pl-display); color: var(--pl-ink); font-size: 1.2rem;
  font-weight: 700; letter-spacing: -.01em;}

/* franja de cifras */
.pl-franja {display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); background: var(--pl-surface);
  border: 1px solid var(--pl-line); border-radius: 14px; overflow: hidden; margin: 4px 0 8px;}
.pl-franja > div {padding: 18px 22px 16px; border-left: 1px solid var(--pl-line); margin-left: -1px;}
.pl-franja .label {font-size: .8rem; color: var(--pl-muted); font-weight: 600;}
.pl-franja .value {font-family: var(--pl-display); font-size: 2.15rem; font-weight: 700; color: var(--pl-ink);
  letter-spacing: -.03em; line-height: 1.1; margin: 6px 0 4px;}
.pl-franja .hint {font-size: .82rem; color: var(--pl-muted); line-height: 1.4;}
.pl-franja .accent .value {color: var(--pl-alta);}
.pl-franja .good .value {color: var(--pl-brand);}

/* tarjetas de lead */
.pl-card {background: var(--pl-surface); border: 1px solid var(--pl-line); border-radius: 14px; padding: 18px 20px;
  height: 100%; transition: border-color .15s ease;}
.pl-card:hover {border-color: #b9cdd5;}
.pl-card.top3 {min-height: 250px; display: flex; flex-direction: column;}
.pl-card .top {display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;}
.pl-rank {font-family: var(--pl-display); color: var(--pl-muted); font-weight: 700; font-size: .95rem;}
.pl-pill {display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 3px 10px;
  font-size: .76rem; font-weight: 600; text-transform: capitalize;}
.pl-pill::before {content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor;}
.pl-pill.alta {background: var(--pl-alta-bg); color: var(--pl-alta);}
.pl-pill.media {background: var(--pl-media-bg); color: var(--pl-media);}
.pl-pill.baja {background: var(--pl-wash); color: var(--pl-muted);}
.pl-card .prob {font-family: var(--pl-display); font-size: 2.1rem; font-weight: 700; color: var(--pl-ink);
  letter-spacing: -.03em; line-height: 1.05;}
.pl-card .prob small {font-family: Inter, sans-serif; font-size: .82rem; font-weight: 500; color: var(--pl-muted);
  letter-spacing: 0; margin-left: 4px;}
.pl-card .meta {font-size: .86rem; color: var(--pl-muted); margin: 8px 0 12px; line-height: 1.55;}
.pl-card .meta b {color: var(--pl-ink); font-weight: 600;}
.pl-card .why {font-size: .87rem; color: #34505c; line-height: 1.55; margin-top: auto; padding-top: 12px;
  border-top: 1px solid var(--pl-line);}

.pl-section {font-family: var(--pl-display); font-size: 1.2rem; font-weight: 700; color: var(--pl-ink);
  letter-spacing: -.015em; margin: 26px 0 10px;}
.pl-muted {color: var(--pl-muted); font-size: .9rem; line-height: 1.55;}
.pl-facts {display: grid; grid-template-columns: 1fr 1fr; gap: 12px 18px; margin: 12px 0 14px;}
.pl-facts div {font-size: .78rem; color: var(--pl-muted); font-weight: 500;}
.pl-facts b {display: block; color: var(--pl-ink); font-size: .95rem; font-weight: 600; margin-top: 2px;}
.pl-wa {background: #e9f6ee; border-radius: 16px 16px 16px 4px; padding: 14px 16px; max-width: 560px;
  font-size: .97rem; line-height: 1.55; color: #12301f; white-space: pre-wrap;}
.pl-formula {background: var(--pl-wash); font-family: var(--pl-display); font-weight: 600; line-height: 1.8;
  border-radius: 12px; padding: 16px 18px; font-size: .98rem; color: var(--pl-ink);}

/* pestañas */
.stTabs [data-baseweb="tab-list"] {gap: 22px; border-bottom: 1px solid var(--pl-line);}
.stTabs [data-baseweb="tab"] {padding: 0 2px 10px; background: transparent;}
.stTabs [data-baseweb="tab"] p {font-family: var(--pl-display); font-size: 1rem; font-weight: 600; color: var(--pl-muted);}
.stTabs [aria-selected="true"] p {color: var(--pl-ink);}
.stTabs [data-baseweb="tab-highlight"] {background: var(--pl-ink); height: 2px;}
.stTabs [data-baseweb="tab-border"] {display: none;}

@media (max-width: 640px) {
  .pl-hero .estado {text-align: left;}
  .pl-hero h1 {font-size: 2rem;}
}
@media (prefers-reduced-motion: reduce) {.pl-card {transition: none;}}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- utilidades
def fecha_txt(d) -> str:
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"


def horas_txt(h: float) -> str:
    if h < 1:
        return f"{max(1, round(h * 60))}\u00a0min"
    return f"{h:.1f}\u00a0h" if h < 24 else f"{round(h)}\u00a0h"


def anuncio_txt(fila) -> str:
    return fila.canal if fila.anuncio == "(sin anuncio)" else f"{fila.canal} · {fila.anuncio}"


def franja(cifras: list) -> None:
    """Fila de cifras unidas en una sola franja: (etiqueta, valor, pista[, clase])."""
    celdas = "".join(f'<div class="{c[3] if len(c) > 3 else ""}"><div class="label">{c[0]}</div>'
                     f'<div class="value">{c[1]}</div><div class="hint">{c[2]}</div></div>' for c in cifras)
    st.markdown(f'<div class="pl-franja">{celdas}</div>', unsafe_allow_html=True)


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
  <div class="why">{escape(fila.razon)}</div>
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
        x=alt.X("pct:Q", title="% de las ventas que quedan en el primer tercio", scale=alt.Scale(domain=[0, 100]),
                  axis=alt.Axis(values=[0, 25, 50, 75, 100])),
        y=y,
        color=alt.condition(alt.datum.nuestro, alt.value("#00547a"), alt.value("#c9d8de")),
        tooltip=[alt.Tooltip("orden:N", title="Orden"), alt.Tooltip("pct:Q", title="%", format=".0f")],
    )
    texto = barras.mark_text(align="left", dx=6, fontSize=14, fontWeight="bold", color="#0e2a36").encode(
        text=alt.Text("pct:Q", format=".0f"), color=alt.value("#0e2a36"))
    azar = alt.Chart(pd.DataFrame({"x": [100 / 3]})).mark_rule(strokeDash=[5, 4], color="#b4232a", size=1.5).encode(x="x:Q")
    nota = alt.Chart(pd.DataFrame({"x": [100 / 3], "t": ["al azar: 33%"]})).mark_text(
        align="left", dx=5, dy=-8, color="#b4232a", fontSize=12).encode(x="x:Q", y=alt.value(0), text="t:N")
    return (barras + texto + azar + nota).properties(height=190).configure(font="Inter").configure_axis(
        grid=False, domainColor="#dbe6ea", tickColor="#dbe6ea", labelColor="#5a6e78", titleColor="#5a6e78").configure_view(stroke=None)


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
    st.markdown("## Primera Llamada")
    st.caption("Lista diaria de llamadas para el equipo de ventas.")

    with st.expander("Datos", expanded=False):
        archivo = st.file_uploader("Cargar otro CSV (mismo formato que leads_ficticios.csv)", type="csv")
    contenido = archivo.getvalue() if archivo else None
    try:
        leads, resumen = cargar(contenido)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    st.markdown("### Día y hora")
    primero = leads.reg.min().normalize() + timedelta(days=7)
    ultimo = leads.reg.max().normalize() + timedelta(days=1)
    dias = {fecha_txt(d) + (" · mañana siguiente a los datos" if d == ultimo else ""): d
            for d in pd.date_range(primero, ultimo)[::-1]}
    dia = dias[st.selectbox("Día", list(dias))]
    hora = st.select_slider("Hora", options=list(range(7, 21)), value=9, format_func=lambda h: f"{h:02d}:00")

    st.markdown("### Asesores de hoy")
    todos = sorted(leads.asesor.dropna().unique()) if "asesor" in leads else []
    asesores = st.multiselect("Asesores", todos, default=todos, label_visibility="collapsed")

    st.markdown("### Validación")
    mostrar = st.toggle("Mostrar qué pasó después", help="Revela el resultado real de cada lead para comprobar el orden.")

    st.markdown("### Asistente de mensajes")
    # La clave vive en los secretos de Streamlit (app publicada) o en .env (en tu computadora), nunca en pantalla.
    try:
        clave = st.secrets.get("OPENROUTER_API_KEY", "") or st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        clave = ""
    clave = clave or clave_del_entorno()
    if clave:
        st.caption("IA conectada (GPT-6 Luna).")
    else:
        st.caption("IA no disponible: el asistente usa una plantilla.")
    usar_guardadas = RESPUESTAS_DEMO.exists() and st.toggle(
        "Usar respuestas guardadas", value=True,
        help="Para la demo: muestra al instante lo que la IA ya escribió para los leads de hoy a las 9:00, "
             "sin depender de la red. Los demás leads se generan en vivo.")

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
detalle = [f"{len(asesores)} asesor{'es' if len(asesores) != 1 else ''}",
           "mensajes con IA" if clave else "mensajes con plantilla"]
if mostrar:
    detalle.append("mostrando qué pasó después")
st.markdown(f"""
<div class="pl-hero">
  <div>
    <div class="marca">Clivi · Ventas</div>
    <h1>Primera Llamada</h1>
    <p>A quién llama primero cada asesor, en orden de probabilidad de venta si se le llama ahora.</p>
  </div>
  <div class="estado"><b>{fecha_txt(dia).capitalize()}, {hora:02d}:00</b>{" · ".join(detalle)}</div>
</div>""", unsafe_allow_html=True)

franja([
    ("Leads en cola", f"{n}", "sin primera llamada, últimas 48 h"),
    ("Prioridad alta", f"{int((lista.prioridad == 'alta').sum()) if n else 0}",
     f"probabilidad ≥ 8% · {urgentes} llegaron hace menos de 15 min", "accent"),
    ("Ventas esperadas", f"{esperadas:.1f}", "si se llama a toda la cola ahora"),
    ("Primer tercio", f"{concentracion:.0%}" if n else "–",
     f"de las ventas esperadas están en los primeros {tercio}", "good"),
])

st.write("")
tab_lista, tab_contacto, tab_modelo = st.tabs(["Lista del día", "Preparar contacto", "Cómo decide y si funciona"])

# ---------------------------------------------------------------- 1. lista
with tab_lista:
    if lista.empty:
        st.info("No hay leads esperando primera llamada a esta hora. Prueba las 9:00 o elige otro día.")
    else:
        st.markdown('<div class="pl-section">Llamar primero</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for col, fila in zip(cols, lista.head(3).itertuples()):
            tarjeta_lead(col, fila, mostrar)

        st.markdown('<div class="pl-section">Lista completa por asesor</div>', unsafe_allow_html=True)
        if not asesores:
            st.warning("Elige al menos un asesor en la barra lateral para repartir la lista.")
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
                        st.info(f"En esta lista hubo **{tot} venta{'s' if tot > 1 else ''}**. "
                                   f"**{top}** {'quedó' if top == 1 else 'quedaron'} en el primer tercio (los primeros {k}).")
                    else:
                        st.info("Ninguno de estos leads terminó comprando. Prueba miércoles 4 nov o lunes 2 nov.")
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
    st.markdown('<div class="pl-muted">Para el lead que elijas: si empezar por llamada o WhatsApp, el mensaje, '
                'el guion y qué hacer si no contesta. Solo usa los datos del registro.</div>', unsafe_allow_html=True)
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
  <div class="why">{escape(fila.razon)}</div>
</div>""", unsafe_allow_html=True)
            st.write("")
            if st.button("Preparar contacto", type="primary", width="stretch"):
                lead = {k: fila.get(k) for k in ["lead_id", "canal", "anuncio", "objetivo", "plan_de_interes", "estado",
                                                 "edad", "horas_esperando", "prioridad", "probabilidad"]}
                lead["hora_actual"] = f"{hora:02d}:00"
                guardada = respuesta_guardada(lead) if usar_guardadas else None
                if guardada is not None:
                    contacto, fuente = guardada, "ia (guardada)"
                else:
                    with st.spinner("Preparando el primer contacto…"):
                        contacto, fuente = preparar_contacto(lead, clave)
                    # Si la IA falla en vivo pero hay una respuesta guardada, mejor esa que la plantilla.
                    if not fuente.startswith("ia") and (respaldo := respuesta_guardada(lead)) is not None:
                        contacto, fuente = respaldo, "ia (guardada)"
                st.session_state["contacto"] = (fila.lead_id, contacto, fuente)

            # ---- qué pasó después del contacto
            st.markdown('<div class="pl-section" style="margin-top:18px">¿Qué pasó con este lead?</div>',
                        unsafe_allow_html=True)
            registrados = registro.leer()
            dia_txt = f"{dia:%Y-%m-%d}"
            previo = registrados[(registrados.lead_id == str(fila.lead_id)) & (registrados.dia == dia_txt)
                                 & (registrados.hora == f"{hora:02d}:00")]
            botones = st.columns(2)
            for j, (clave_res, etiqueta) in enumerate(registro.RESULTADOS.items()):
                if botones[j % 2].button(etiqueta, key=f"res_{clave_res}", width="stretch"):
                    guardado_c = st.session_state.get("contacto")
                    mismo = guardado_c and guardado_c[0] == fila.lead_id
                    try:
                        registro.registrar({
                            "dia": dia_txt, "hora": f"{hora:02d}:00", "lead_id": str(fila.lead_id),
                            "asesor": fila.asignado, "prioridad": fila.prioridad,
                            "probabilidad": round(float(fila.probabilidad), 4),
                            "canal_recomendado": guardado_c[1].canal_recomendado if mismo else "",
                            "fuente_mensaje": guardado_c[2] if mismo else "", "resultado": clave_res})
                        st.toast(f"Guardado: {fila.lead_id} · {etiqueta}")
                        previo = registro.leer().pipe(lambda t: t[(t.lead_id == str(fila.lead_id)) & (t.dia == dia_txt)
                                                                    & (t.hora == f"{hora:02d}:00")])
                    except OSError:
                        st.error("No se pudo guardar el resultado en este equipo.")
            if not previo.empty:
                st.caption(f"Registrado: **{registro.RESULTADOS[previo.resultado.iloc[-1]]}** "
                           f"({previo.registrado.iloc[-1][11:16]}). Puedes cambiarlo con otro botón.")
            else:
                st.caption("Márcalo después de llamar o escribir. Con estos datos se recalibra la prioridad.")

        with der:
            guardado = st.session_state.get("contacto")
            if not guardado or guardado[0] != fila.lead_id:
                st.markdown('<div class="pl-card" style="text-align:center; padding:48px 24px;">'
                            '<div class="pl-section" style="margin-top:0">Elige un lead y presiona “Preparar contacto”</div>'
                            '<div class="pl-muted">Aquí aparecen el canal recomendado, el WhatsApp, '
                            'el guion de llamada y las objeciones probables.</div></div>', unsafe_allow_html=True)
            else:
                lid, c, fuente = guardado
                st.info(f"**Empezar por {c.canal_recomendado}.** {c.por_que_canal}")
                st.caption(("Escrito con IA (GPT-6 Luna)" + (" · corregido automáticamente" if "corregida" in fuente else "")
                            + (" · respuesta guardada" if "guardada" in fuente else ""))
                           if fuente.startswith("ia") else f"Usando {fuente}")
                with st.container(border=True):
                    st.markdown("**WhatsApp**")
                    st.markdown(f'<div class="pl-wa">{escape(c.whatsapp)}</div>', unsafe_allow_html=True)
                    with st.expander("Copiar texto"):
                        st.code(c.whatsapp, language=None, wrap_lines=True)
                a, b = st.columns(2)
                with a, st.container(border=True):
                    st.markdown("**Guion de llamada**")
                    st.write(c.guion_apertura)
                    st.markdown("**Preguntas para entender su caso**")
                    st.markdown("\n".join(f"{j}. {p}" for j, p in enumerate(c.preguntas, 1)))
                with b, st.container(border=True):
                    st.markdown("**Objeciones probables**")
                    st.markdown("\n".join(f"- {o}" for o in c.objeciones))
                    st.markdown("**Si no contesta**")
                    st.write(c.si_no_contesta)

# ---------------------------------------------------------------- 3. modelo y validación
with tab_modelo:
    v = validacion(contenido)
    if v["ventas"]:
        pct = {k: 100 * v[k] / v["ventas"] for k in ("primera_llamada", "orden_real", "orden_llegada")}
        st.markdown('<div class="pl-section">¿Funciona? Ventas que quedan en el primer tercio de la lista de las 9:00</div>',
                    unsafe_allow_html=True)
        franja([
            ("Primera Llamada", f"{pct['primera_llamada']:.0f}%",
             f"{v['primera_llamada']} de {v['ventas']} ventas en el primer tercio", "good"),
            ("Orden real de los asesores", f"{pct['orden_real']:.0f}%", f"{v['orden_real']} de {v['ventas']} ventas"),
            ("Orden de llegada", f"{pct['orden_llegada']:.0f}%", f"{v['orden_llegada']} de {v['ventas']} ventas"),
        ])
        st.altair_chart(grafica_validacion(pct), use_container_width=True)
        st.caption(f"{v['mananas']} mañanas, {v['leads']} leads en cola, {v['ventas']} ventas. "
                   f"Cada día el modelo solo aprende de días anteriores. Un tercio al azar daría 33%.")

    # ---- lo que registran los asesores
    st.markdown('<div class="pl-section">Lo que registran los asesores</div>', unsafe_allow_html=True)
    hechos = registro.leer()
    if hechos.empty:
        st.info("Todavía no hay resultados registrados. En **Preparar contacto**, marca qué pasó con cada lead "
                "(contestó, no contestó, compró o no le interesa) y aquí verás si la prioridad acierta.")
    else:
        r = registro.resumen(hechos)
        contestaron = int(r.contestaron.sum())
        franja([
            ("Leads registrados", f"{len(hechos)}",
             f"{hechos.dia.nunique()} día(s) · {hechos.asesor.nunique()} asesor(es)"),
            ("Contestaron", f"{contestaron / len(hechos):.0%}", f"{contestaron} de {len(hechos)}"),
            ("Compraron", f"{int(r.compraron.sum())}", "ventas registradas", "good"),
        ])
        st.dataframe(r, hide_index=True, width="stretch",
                     column_config={"prioridad": st.column_config.TextColumn("Prioridad"),
                                    "registrados": st.column_config.NumberColumn("Registrados"),
                                    "contestaron": st.column_config.NumberColumn("Contestaron"),
                                    "compraron": st.column_config.NumberColumn("Compraron"),
                                    "tasa_compra": st.column_config.ProgressColumn("Compra", format="percent",
                                                                                   min_value=0, max_value=1)})
        st.caption("Si la prioridad acierta, la columna Compra baja de alta a media a baja.")
        st.download_button("Descargar registros (CSV)", hechos.to_csv(index=False).encode("utf-8"),
                           "resultados_registrados.csv", "text/csv")

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
        st.markdown("**Efecto del tiempo esperando**")
        st.dataframe(modelo.tabla_efecto(), hide_index=True, width="stretch",
                     column_config={"si se le llama": st.column_config.TextColumn("Si se le llama"),
                                    "efecto": st.column_config.NumberColumn("Efecto", format="×%.2f")})
        st.caption("Llamar en los primeros 15 minutos multiplica la probabilidad; después de 12 h cae a menos de la mitad.")
    with f3:
        st.markdown("**Tasa de venta por anuncio**")
        st.dataframe(modelo.tabla_anuncios().assign(tasa_venta=lambda t: t.tasa_venta * 100), hide_index=True,
                     width="stretch", height=260,
                     column_config={"canal": st.column_config.TextColumn("Canal", width="small"),
                                    "anuncio": st.column_config.TextColumn("Anuncio", width="medium"),
                                    "leads": st.column_config.NumberColumn("Leads", width="small"),
                                    "tasa_venta": st.column_config.ProgressColumn("Venta", format="%.1f%%", width="medium",
                                                                                  min_value=0, max_value=20)})

    # ---- cómo mejoramos la IA
    st.markdown('<div class="pl-section">Cómo se mejoró el asistente</div>', unsafe_allow_html=True)
    st.markdown('<div class="pl-muted">Cada versión se probó con la IA real sobre los mismos 12 leads variados '
                '(prioridad alta, media y baja; recién llegados y de más de 12 h; peso y diabetes), y una revisión '
                'automática contó cuántos mensajes rompen alguna regla y cuántas objeciones son genéricas.</div>',
                unsafe_allow_html=True)
    st.markdown(
        "| Versión | Pasan las reglas | Objeciones genéricas | Qué cambió |\n"
        "|---|:---:|:---:|---|\n"
        "| 1. Primera versión | 12 de 12 | — | No se presentaba como Clivi, citaba «Meta» y se disculpaba sin razón |\n"
        "| 2. Reglas más claras | 12 de 12 | — | Todos se presentan como asesor de Clivi |\n"
        "| 3. Ejemplos de buenas respuestas | 12 de 12 | 22 de 24 | Mejor tono, pero objeciones de cajón («lo voy a pensar», «está caro») |\n"
        "| 4. Pistas por tipo de lead | 11 de 12 | 1 de 24 | Objeciones según canal, objetivo, edad, plan y horas esperando |\n"
        "| **5. Pistas + autocorrección** | **12 de 12** | **0 de 24** | Si un mensaje rompe una regla, la IA lo corrige sola una vez |\n"
        "| Demo: 42 leads de las 9:00 | 41 de 42 | — | Respuestas guardadas para que la demo no dependa de la red |")
    st.write("")
    i1, i2 = st.columns([1, 1], gap="large")
    with i1:
        st.markdown("**Reglas que revisa en cada mensaje**")
        st.markdown("- WhatsApp de máximo 3 frases que termina en pregunta\n"
                    "- Dice que es de Clivi y menciona el objetivo del lead\n"
                    "- Sin promesas médicas, medicamentos ni precios inventados\n"
                    "- Sin nombres inventados ni «me comentaste»\n"
                    "- Se disculpa solo si el lead lleva más de 12 h esperando\n"
                    "- Prioridad alta → recomienda llamar")
    with i2:
        st.markdown("**Siguiente paso: aprender de resultados reales**")
        st.markdown("1. Los asesores marcan qué pasó con cada lead (botones en *Preparar contacto*).\n"
                    "2. Cada semana se recalibra la prioridad con esos resultados.\n"
                    "3. Los mensajes que terminaron en venta se vuelven los ejemplos de la IA; "
                    "con cientos de casos ya se puede afinar el modelo (fine-tuning).")
