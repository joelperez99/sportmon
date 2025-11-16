# footystats_corners_streamlit.py
# ----------------------------------------------------
# Streamlit: Buscar partidos con alto potencial de CÓRNERS
# usando FootyStats Football Data API (api.football-data-api.com)
# ----------------------------------------------------
# Reqs:
#   pip install streamlit requests pandas
#
# Cómo correr:
#   streamlit run footystats_corners_streamlit.py
# ----------------------------------------------------

import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://api.football-data-api.com"


# ======================================================
# Clase principal
# ======================================================

class FootyStatsCornersFinder:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Debes proporcionar tu API key de FootyStats.")
        self.api_key = api_key

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if params is None:
            params = {}
        params.setdefault("key", self.api_key)

        url = f"{BASE_URL}/{path.lstrip('/')}"
        resp = requests.get(url, params=params, timeout=25)

        if not resp.ok:
            raise RuntimeError(
                f"Error en petición GET {url} "
                f"({resp.status_code}): {resp.text[:400]}"
            )
        # FootyStats a veces devuelve lista directamente, a veces dict
        try:
            return resp.json()
        except Exception:
            raise RuntimeError(f"Respuesta no es JSON válida: {resp.text[:400]}")

    # ---------- 1) Partidos por fecha ----------
    def get_matches_by_date(
        self,
        date_str: str,
        timezone: str = "Etc/UTC",
    ) -> List[Dict[str, Any]]:
        """
        Usa endpoint:
        GET /todays-matches?key=YOURKEY&date=YYYY-MM-DD&timezone=Etc/UTC
        Devuelve lista de partidos de esa fecha (máx 200).
        """
        data = self._get(
            "/todays-matches",
            params={"date": date_str, "timezone": timezone},
        )

        # Puede venir como lista directa o dict con "data"
        if isinstance(data, list):
            matches = data
        elif isinstance(data, dict):
            matches = data.get("data", []) or []
        else:
            matches = []

        return matches

    # ---------- 2) Detalle de partido ----------
    def get_match_details(self, match_id: int) -> Dict[str, Any]:
        """
        Usa endpoint:
        GET /match?key=YOURKEY&match_id=ID
        Devuelve stats completos, incluyendo corners_potential, corners_o85_potential, etc.
        """
        data = self._get(
            "/match",
            params={"match_id": match_id},
        )

        # Si viniera como lista de un solo elemento, tomamos el primero
        if isinstance(data, list):
            return data[0] if data else {}
        elif isinstance(data, dict):
            # Algunos planes devuelven {"data": {...}}
            if "data" in data and isinstance(data["data"], dict):
                return data["data"]
            return data
        else:
            return {}

    # ---------- 3) DataFrame de partidos con info de corners ----------
    def build_corners_dataframe(
        self,
        matches: List[Dict[str, Any]],
        min_corners_potential: float = 0.0,
    ) -> pd.DataFrame:
        filas = []

        for m in matches:
            match_id = m.get("id")
            if match_id is None:
                continue

            # IDs básicos desde todays-matches
            home_id = m.get("homeID")
            away_id = m.get("awayID")
            total_corners = m.get("totalCornerCount")
            date_unix = m.get("date_unix")

            # Detalles (incluye stats pre-match)
            try:
                details = self.get_match_details(match_id)
            except Exception:
                details = {}

            corners_potential = details.get("corners_potential")

            # Filtrado por potencial de corners (si se configuró y el valor existe)
            if (
                min_corners_potential is not None
                and corners_potential is not None
                and float(corners_potential) < float(min_corners_potential)
            ):
                continue

            # Otros campos de interés (si existen)
            c_o85 = details.get("corners_o85_potential")
            c_o95 = details.get("corners_o95_potential")
            c_o105 = details.get("corners_o105_potential")

            # Algunos planes incluyen nombres; si no, se quedarán en None
            home_name = details.get("home_name") or details.get("team_a_name")
            away_name = details.get("away_name") or details.get("team_b_name")
            league_name = details.get("competition_name")

            filas.append(
                {
                    "Match ID": match_id,
                    "Home ID": home_id,
                    "Away ID": away_id,
                    "Home Name": home_name,
                    "Away Name": away_name,
                    "League": league_name,
                    "Fecha UNIX": date_unix,
                    "Total Corners (actual)": total_corners,
                    "corners_potential": corners_potential,
                    "corners_o85_potential": c_o85,
                    "corners_o95_potential": c_o95,
                    "corners_o105_potential": c_o105,
                }
            )

        if not filas:
            return pd.DataFrame(
                columns=[
                    "Match ID",
                    "Home ID",
                    "Away ID",
                    "Home Name",
                    "Away Name",
                    "League",
                    "Fecha UNIX",
                    "Total Corners (actual)",
                    "corners_potential",
                    "corners_o85_potential",
                    "corners_o95_potential",
                    "corners_o105_potential",
                ]
            )

        df = pd.DataFrame(filas)
        # Ordenamos por mayor corners_potential si existe
        if "corners_potential" in df.columns:
            df = df.sort_values("corners_potential", ascending=False)
        return df


# ======================================================
# STREAMLIT APP
# ======================================================

def main():
    st.set_page_config(
        page_title="Corners Finder — FootyStats",
        page_icon="🏟️",
        layout="wide",
    )

    st.title("🏟️ Corners Finder — FootyStats API")
    st.write(
        "App para encontrar **partidos con alto potencial de córners** "
        "usando la API de FootyStats (football-data-api.com)."
    )

    st.sidebar.header("Configuración")

    api_key = st.sidebar.text_input(
        "FootyStats API Key",
        type="password",
        help="Pega aquí tu API key de FootyStats.",
    )

    fecha = st.sidebar.date_input(
        "Fecha",
        value=datetime.date.today(),
        help="Fecha de los partidos a analizar.",
    )
    fecha_str = fecha.strftime("%Y-%m-%d")

    timezone = st.sidebar.text_input(
        "Timezone (opcional)",
        value="Etc/UTC",
        help="Formato TZ, por ejemplo 'Europe/London', 'America/Mexico_City'. "
             "Si lo dejas vacío, se usa Etc/UTC.",
    ) or "Etc/UTC"

    min_corners_potential = st.sidebar.number_input(
        "Mínimo corners_potential",
        min_value=0.0,
        max_value=30.0,
        value=0.0,
        step=0.5,
        help=(
            "Filtra partidos cuyo `corners_potential` (promedio de córners "
            "pre-partido) sea al menos este valor. Deja 0 si no quieres filtrar."
        ),
    )

    buscar_btn = st.sidebar.button("🔍 Buscar partidos con potencial de corners")

    st.markdown("---")

    if not buscar_btn:
        st.info(
            "Configura tu API key y la fecha en la barra lateral y luego haz clic en "
            "**“Buscar partidos con potencial de corners”**."
        )
        return

    if not api_key:
        st.error("Debes ingresar tu **FootyStats API key**.")
        return

    try:
        finder = FootyStatsCornersFinder(api_key)

        # 1) Partidos por fecha
        st.subheader(f"Partidos para la fecha {fecha_str}")
        with st.spinner("Cargando partidos desde FootyStats..."):
            matches = finder.get_matches_by_date(fecha_str, timezone=timezone)

        st.write(f"Total de partidos devueltos por la API: `{len(matches)}`")

        if not matches:
            st.warning("La API no devolvió partidos para esa fecha (revisa ligas activas en tu cuenta).")
            return

        # 2) Construir tabla con info de corners
        with st.spinner("Calculando potencial de corners por partido..."):
            df_resultados = finder.build_corners_dataframe(
                matches,
                min_corners_potential=min_corners_potential,
            )

        st.markdown("## ✅ Partidos con **stats de corners**")

        if df_resultados.empty:
            st.warning(
                "No se encontraron partidos que cumplan con el filtro de `corners_potential`. "
                "Prueba bajando el mínimo o verifica qué devuelve la API para esa fecha."
            )
        else:
            st.success(
                f"Se encontraron `{len(df_resultados)}` partidos con información de corners "
                f"(filtrados por corners_potential ≥ {min_corners_potential})."
            )
            st.dataframe(df_resultados, use_container_width=True)

            # Descargar CSV
            csv = df_resultados.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Descargar resultados en CSV",
                data=csv,
                file_name=f"footystats_corners_{fecha_str}.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error("Ocurrió un error al consultar la API de FootyStats.")
        st.code(str(e))


if __name__ == "__main__":
    main()
