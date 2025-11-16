# corners_sportmonks_streamlit.py
# ----------------------------------------------------
# Streamlit: Buscar partidos con apuestas de CÓRNERS
# usando Sportmonks Football API v3.
# ----------------------------------------------------

import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://api.sportmonks.com/v3"
FOOTBALL_BASE = f"{BASE_URL}/football"


# ======================================================
# Clase principal
# ======================================================

class SportmonksCornersFinder:
    def __init__(self, api_token: str):
        if not api_token:
            raise ValueError("Debes proporcionar tu API token de Sportmonks.")
        self.api_token = api_token

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
        params.setdefault("api_token", self.api_token)

        resp = requests.get(url, params=params, timeout=25)
        if not resp.ok:
            raise RuntimeError(
                f"Error en petición GET {url} "
                f"({resp.status_code}): {resp.text[:400]}"
            )
        return resp.json()

    # ---------- Fixtures por fecha ----------
    def get_fixtures_by_date_with_odds(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Fixtures por fecha que tengan odds.
        GET /v3/football/fixtures/date/{date}?filters=havingOdds&include=league;participants
        """
        url = f"{FOOTBALL_BASE}/fixtures/date/{date_str}"
        params = {
            "filters": "havingOdds",
            "include": "league;participants",
        }
        data = self._get(url, params=params)
        return data.get("data", []) if isinstance(data, dict) else data or []

    # ---------- Fixtures por round ----------
    def get_fixtures_by_round_with_odds(self, round_id: int) -> List[Dict[str, Any]]:
        """
        Fixtures de un round con odds.
        GET /v3/football/rounds/{id}?include=fixtures.league;fixtures.participants
        """
        url = f"{FOOTBALL_BASE}/rounds/{round_id}"
        params = {
            "include": "fixtures.league;fixtures.participants",
        }
        data = self._get(url, params=params)
        round_data = data.get("data") if isinstance(data, dict) else {} or {}

        fixtures_raw = round_data.get("fixtures") or []

        # Puede venir como dict con data o como lista directa
        if isinstance(fixtures_raw, dict):
            fixtures = fixtures_raw.get("data", []) or []
        elif isinstance(fixtures_raw, list):
            fixtures = fixtures_raw
        else:
            fixtures = []

        fixtures_with_odds = [fx for fx in fixtures if fx.get("has_odds")]
        return fixtures_with_odds

    # ---------- Odds de CÓRNERS por fixture ----------
    def get_corner_odds_for_fixture(
        self,
        fixture_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Pide TODAS las pre-match odds del fixture y filtra las que
        tengan 'corner' en la descripción del mercado.

        GET /v3/football/odds/pre-match/fixtures/{ID}
        """
        url = f"{FOOTBALL_BASE}/odds/pre-match/fixtures/{fixture_id}"
        data = self._get(url)

        if isinstance(data, dict):
            odds_list = data.get("data", []) or []
        else:
            odds_list = data or []

        corner_odds = []
        for o in odds_list:
            desc = (o.get("market_description") or "").lower()
            # aquí puedes afinar el filtro si ves otro texto
            if "corner" in desc:
                corner_odds.append(o)

        return corner_odds

    # ---------- DataFrame con partidos que sí tienen corners ----------
    def build_corners_dataframe(
        self,
        fixtures: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        filas = []

        for fx in fixtures:
            fixture_id = fx.get("id")
            starting_at = fx.get("starting_at")

            # Liga
            league = fx.get("league") or {}
            if isinstance(league, dict):
                league_data = league.get("data") or league
            else:
                league_data = {}
            league_name = league_data.get("name")

            # Equipos (participants con meta.location)
            home_name = None
            away_name = None
            participants_raw = fx.get("participants") or []

            if isinstance(participants_raw, dict):
                participants = participants_raw.get("data", []) or []
            elif isinstance(participants_raw, list):
                participants = participants_raw
            else:
                participants = []

            for p in participants:
                meta = p.get("meta") or {}
                loc = (meta.get("location") or "").lower()
                name = p.get("name")
                if loc == "home":
                    home_name = name
                elif loc == "away":
                    away_name = name

            try:
                corner_odds = self.get_corner_odds_for_fixture(fixture_id)
            except Exception:
                corner_odds = []

            if corner_odds:
                filas.append(
                    {
                        "Fixture ID": fixture_id,
                        "Fecha/hora": starting_at,
                        "Liga": league_name,
                        "Local": home_name,
                        "Visitante": away_name,
                        "Líneas corners (total)": len(corner_odds),
                    }
                )

        if not filas:
            return pd.DataFrame(
                columns=[
                    "Fixture ID",
                    "Fecha/hora",
                    "Liga",
                    "Local",
                    "Visitante",
                    "Líneas corners (total)",
                ]
            )

        df = pd.DataFrame(filas)
        if "Fecha/hora" in df.columns:
            df = df.sort_values("Fecha/hora")
        return df


# ======================================================
# STREAMLIT APP
# ======================================================

def main():
    st.set_page_config(
        page_title="Corners Finder — Sportmonks",
        page_icon="⚽",
        layout="wide",
    )

    st.title("⚽ Corners Finder — Sportmonks (API v3)")
    st.write(
        "App para encontrar **partidos que sí tienen mercados de tiros de esquina** "
        "usando la API de Sportmonks."
    )

    st.sidebar.header("Configuración")

    api_token = st.sidebar.text_input(
        "API Token de Sportmonks",
        type="password",
        help="Pega tu api_token de Sportmonks (API v3).",
    )

    modo = st.sidebar.radio(
        "Modo de búsqueda",
        ["Por fecha", "Por Round ID"],
    )

    if modo == "Por fecha":
        fecha = st.sidebar.date_input(
            "Fecha",
            value=datetime.date.today(),
            help="Fecha de los partidos que quieres revisar.",
        )
        fecha_str = fecha.strftime("%Y-%m-%d")
        round_id = None
    else:
        round_id = st.sidebar.number_input(
            "Round ID",
            min_value=1,
            step=1,
            help="Round ID para usar GET Round by ID.",
        )
        fecha_str = None

    buscar_btn = st.sidebar.button("🔍 Buscar partidos con corners")

    st.markdown("---")

    if not buscar_btn:
        st.info(
            "Configura el token y los parámetros en la barra lateral y luego haz clic en "
            "**“Buscar partidos con corners”**."
        )
        return

    if not api_token:
        st.error("Debes ingresar tu **API Token** de Sportmonks.")
        return

    try:
        finder = SportmonksCornersFinder(api_token)

        # 1) Fixtures según el modo
        if modo == "Por fecha":
            st.subheader(f"Fixtures con odds en la fecha {fecha_str}")
            with st.spinner("Cargando fixtures por fecha (solo los que tienen odds)..."):
                fixtures = finder.get_fixtures_by_date_with_odds(fecha_str)
        else:
            st.subheader(f"Fixtures con odds en el round {int(round_id)}")
            with st.spinner("Cargando fixtures del round (solo los que tienen odds)..."):
                fixtures = finder.get_fixtures_by_round_with_odds(int(round_id))

        st.write(f"Total de fixtures con **algún tipo de odds**: `{len(fixtures)}`")

        if not fixtures:
            st.warning("No se encontraron fixtures con odds para esos parámetros.")
            return

        # 2) Filtrar los que tienen corners
        with st.spinner("Filtrando fixtures que tienen mercados de corners..."):
            df_resultados = finder.build_corners_dataframe(fixtures)

        st.markdown("## ✅ Partidos con apuestas de **corners**")

        if df_resultados.empty:
            st.warning(
                "De los fixtures con odds encontrados, ninguno tiene mercados de corners "
                "(según 'market_description' contenga la palabra 'corner')."
            )
        else:
            st.success(
                f"Se encontraron `{len(df_resultados)}` partidos con **apuestas de corners**."
            )
            st.dataframe(df_resultados, use_container_width=True)

            # Botón para descargar CSV
            csv = df_resultados.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Descargar resultados en CSV",
                data=csv,
                file_name="corners_sportmonks.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error("Ocurrió un error al consultar la API de Sportmonks.")
        st.code(str(e))


if __name__ == "__main__":
    main()
