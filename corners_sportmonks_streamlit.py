# app_links_streamlit.py
# -----------------------------------------
# Streamlit – Extractor sencillo de links
# -----------------------------------------

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Extractor de links", page_icon="🔗", layout="wide")

st.title("🔗 Extractor de links de una página web")
st.write("Ingresa una URL y obtén todos los enlaces <a href> de esa página.")

# ========= ENTRADA =========
url = st.text_input("URL de la página", value="https://example.com")

if st.button("Extraer links"):
    if not url.strip():
        st.error("Ingresa una URL válida.")
    else:
        # Asegurarnos de que tenga http/https
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url.strip()

        try:
            st.info(f"Solicitando: {url}")
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            data = []
            for a in soup.find_all("a"):
                href = a.get("href")
                if not href:
                    continue

                texto = (a.get_text(strip=True) or "").strip()
                href_abs = urljoin(url, href)

                data.append({
                    "texto_visible": texto,
                    "href": href,
                    "href_absoluta": href_abs,
                })

            if not data:
                st.warning("No se encontraron enlaces <a> en la página.")
            else:
                df = pd.DataFrame(data)
                st.success(f"Se encontraron {len(df)} links.")
                st.dataframe(df, use_container_width=True)

                # Descargar CSV
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📥 Descargar CSV",
                    data=csv,
                    file_name="links_extraidos.csv",
                    mime="text/csv"
                )

        except requests.exceptions.RequestException as e:
            st.error("Error al hacer la petición HTTP.")
            st.code(str(e))
        except Exception as e:
            st.error("Ocurrió un error inesperado.")
            st.code(str(e))
