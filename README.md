# Primera Llamada

Herramienta para la Misión A del Reto Clivi: cada mañana arma la lista de leads que siguen sin primera llamada, la ordena por probabilidad de venta si se les llama ahora y la reparte entre los asesores que trabajan ese día. Un asistente con IA prepara el primer contacto con cada lead.

```
probabilidad = tasa de venta del anuncio × efecto del tiempo esperando
```

- **Tasa de venta del anuncio:** ventas / leads de ese anuncio, suavizada hacia la tasa de su canal (K = 30) para que un anuncio con pocos datos no exagere.
- **Efecto del tiempo esperando:** ventas observadas / ventas esperadas solo por el anuncio, en cuatro tramos (menos de 15 min, 15 a 60 min, 1 a 12 h, más de 12 h). Con los datos de la intro sale ×2.37, ×1.33, ×1.08 y ×0.44.
- El modelo de cada día aprende **solo de los días anteriores**.

## Resultado

En 28 mañanas (12 oct a 8 nov), con la cola de las 9:00 (833 leads, 30 ventas):

| Orden | Ventas en el primer tercio |
|---|---|
| Primera Llamada | 21 de 30 (70%) |
| Orden real de los asesores | 13 de 30 (43%) |
| Orden de llegada | 6 de 30 (20%) |

Un tercio al azar daría 33%. Son pocas ventas, así que el siguiente paso es una prueba A/B de dos semanas.

## Asistente de seguimiento (IA)

Para el lead que elijas, el asistente (GPT-6 Luna con salida estructurada, por OpenRouter `openai/gpt-6-luna` o directo con OpenAI `gpt-6-luna`; se cambia con la variable `MODELO_IA`) decide si empezar por llamada o WhatsApp y escribe:

- el WhatsApp listo para enviar (máximo 3 frases, termina en pregunta),
- la apertura de la llamada y 3 preguntas para entender el caso,
- 2 objeciones probables con su respuesta,
- qué hacer y cuándo reintentar si no contesta.

Usa lo que se sabe del lead: anuncio, objetivo, plan, horas esperando y prioridad. No promete resultados médicos ni inventa servicios. Si no hay clave de API o la API falla, usa una plantilla fija y la app lo indica.

Para activarlo, usa una de estas opciones:

- **recomendado:** copia `.env.example` como `.env` y pon ahí tu clave (`.env` está en `.gitignore`, no se sube); la app y `probar_ia.py` la leen solas,
- escribe la clave en la barra lateral de la app (una clave `sk-or-...` usa OpenRouter; una `sk-...` usa OpenAI),
- `export OPENROUTER_API_KEY=...` (u `OPENAI_API_KEY`) antes de `streamlit run app.py`,
- en Streamlit Cloud, agrega `OPENROUTER_API_KEY` en *Settings → Secrets*.

Nunca subas la clave al repositorio: `.env` y `.streamlit/secrets.toml` están en `.gitignore`.

## Cómo correrla

```bash
pip install -r requirements.txt
streamlit run app.py          # abre la app en el navegador
python validar.py             # imprime la validación en la terminal
python -m pytest              # corre las pruebas
python probar_ia.py           # prueba la IA real con 12 leads y escribe reporte_ia.md
python guardar_demo.py        # guarda las respuestas de la IA para la demo
```

### Modo demo (respuestas guardadas)

`guardar_demo.py` le pide a la IA el primer contacto de todos los leads de la lista que abre la app (mañana siguiente a los datos, 9:00) y lo guarda en `data/respuestas_demo.json`. Con el interruptor **Usar respuestas guardadas** (barra lateral, encendido por defecto) la app las muestra al instante, sin depender de la red. Los demás leads se generan en vivo, y si la IA falla en vivo para un lead guardado se usa la respuesta guardada en lugar de la plantilla.

La app usa `data/leads_ficticios.csv` por defecto. Desde la barra lateral se puede subir otro CSV con las mismas columnas; se limpia solo (fechas DD/MM y teléfonos repetidos).

## Publicarla gratis (Streamlit Community Cloud)

1. Entra a https://share.streamlit.io con tu cuenta de GitHub y presiona **Create app → Deploy a public app from GitHub**.
2. Repositorio `CesarYamadaX/Clivi`, rama `main`, archivo principal `app.py`. Elige una URL (por ejemplo `primera-llamada-clivi`).
3. En **Advanced settings**: Python 3.12 y en *Secrets* pega `OPENROUTER_API_KEY = "sk-or-..."` (con comillas). Sin secreto la app funciona con las respuestas guardadas y la plantilla.
4. **Deploy**. Tarda 2 o 3 minutos la primera vez; cada push a `main` la actualiza sola.

## Archivos

| Archivo | Qué hace |
|---|---|
| `primera_llamada/modelo.py` | Limpieza, modelo, cola, reparto y validación |
| `primera_llamada/agente.py` | Asistente de seguimiento con IA (y plantilla sin IA) |
| `app.py` | Pantalla en Streamlit |
| `validar.py` | Validación desde la terminal |
| `primera_llamada/revision.py` | Revisa automáticamente cada mensaje (máx. 3 frases, sin promesas médicas, sin nombres inventados, precios reales, etc.) |
| `primera_llamada/demo.py` y `guardar_demo.py` | Respuestas de la IA guardadas para la demo (`data/respuestas_demo.json`) |
| `probar_ia.py` | Prueba la IA real con leads variados y deja el detalle en `reporte_ia.md` |
| `tests/` | Pruebas: limpieza, orden, reparto, que no use el futuro, números de la validación y el asistente con la API simulada |
| `data/leads_ficticios.csv` | Datos de la Introducción |
| `web/` | Versión de página web (un solo HTML, sin instalar nada) |

## Cómo se construyó

Con Claude Code: exploración de los datos en Python, el modelo, la validación, la app y las pruebas. Las decisiones (qué medir, qué variables dejar fuera, cómo validar sin ver el futuro) y la revisión de que los números coincidan están documentadas en la bitácora.
