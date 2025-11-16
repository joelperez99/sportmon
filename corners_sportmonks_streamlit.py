# app_caliente_ids.py
# Streamlit — Obtener IDs de partidos (eventId) desde Caliente Futbol

import re
import requests
import pandas as pd
import streamlit as st

# ===================== FUNCIÓN PRINCIPAL =====================

def get_match_ids_from_html(url: str):
    """
    Descarga el HTML de la página y extrae todos los eventId que encuentre.
    Regresa una lista de IDs únicos como strings.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    }

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # Busca "eventId":123456 o "eventId":"123456"
    ids = re.findall(r'"eventId"\s*:\s*"?(\d+)"?', html)

    # Quita duplicados y ordena
    unique_ids = sorted(set(ids), key=int)
    return unique_ids

# ===================== UI STREAMLIT =====================

st.set_page_config(page_title="IDs Caliente Futbol", page_icon="⚽", layout="centered")

st.title("⚽ Obtener IDs de partidos de Caliente.mx")
st.caption("Extrae los `eventId` desde la página de Futbol.")

default_url = "https://sports.caliente.mx/es_MX/Futbol"
url = st.text_input("URL de la página de Futbol", value=default_url)

if st.button("🔍 Obtener IDs de partidos"):
    if not url.strip():
        st.error("Por favor ingresa una URL válida.")
    else:
        try:
            with st.spinner("Descargando página y extrayendo IDs..."):
                ids = get_match_ids_from_html(url)

            if ids:
                st.success(f"Se encontraron {len(ids)} IDs de partido.")
                df = pd.DataFrame({"eventId": ids})
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Descargar IDs en CSV",
                    data=csv,
                    file_name="caliente_event_ids.csv",
                    mime="text/csv",
                )
            else:
                st.warning("No se encontró ningún `eventId` en el HTML. "
                           "Es posible que Caliente cargue los partidos vía API/JS.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
            st.stop()

st.markdown("---")
st.markdown(
    "💡 Tip: si no encuentra IDs, habría que copiar la URL del endpoint de la API "
    "desde **F12 → Network** y hacer otro script que consuma directamente ese JSON."
)
