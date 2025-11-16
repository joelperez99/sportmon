# app_links_streamlit.py
# -----------------------------------------
# Streamlit – Extractor de links de una página web
# Requisitos:
#   pip install streamlit requests beautifulsoup4 pandas
# Ejecutar con:
#   streamlit run app_links_streamlit.py
# -----------------------------------------

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

import pandas as pd
import streamlit as st

# ================= CONFIG BÁSICA =================
st.set_page_config(
    page_title="Extractor de links",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 Extractor de links de una página web")
st.write("Ingresa una URL y obtén todos los enlaces (`<a href>`).")

# ================= ENTRADA DE USUARIO =================
url_input = st.text_input("URL de la página", value="https://")

col1, col2 = st.columns([1, 3])
with col1:
    extraer = st.button("Extraer links")

# ================= FUNCIÓN PRINCIPAL =================
def extraer_links(url: str):
    # Asegurar que tenga esquema
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    data = []
    for a in soup.find_all("a"):
        href = a.get("href")
        texto = (a.get_text(strip=True) or "").strip()
        target = a.get("target")
        rel = ", ".join(a.get("rel")) if a.get("rel") else ""

        if not href:
            continue

        # Resolver URL absoluta
        href_absoluta = urljoin(url, href)

        data.append({
            "texto_visible": texto,
            "href_original": href,
            "href_absoluta": href_absoluta,
            "target": target,
            "rel": rel
        })

    df = pd.DataFrame(data)
    return df

# ================= LÓGICA DE UI =================
if extraer:
    if not url_input or url_input.strip() == "" or url_input.strip() == "https://":
        st.error("Por favor ingresa una URL válida.")
    else:
        try:
            with st.spinner("Extrayendo links..."):
                df_links = extraer_links(url_input.strip())

            if df_links.empty:
                st.warning("No se encontraron enlaces `<a>` en la página.")
            else:
                st.success(f"Se encontraron {len(df_links)} links.")

                st.subheader("Vista previa de los links")
                st.dataframe(df_links, use_container_width=True)

                # Botón para descargar CSV
                csv = df_links.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="📥 Descargar links en CSV",
                    data=csv,
                    file_name="links_extraidos.csv",
                    mime="text/csv"
                )

        except requests.exceptions.RequestException as e:
            st.error(f"Error al solicitar la página: {e}")
        except Exception as e:
            st.error(f"Ocurrió un error inesperado: {e}")
