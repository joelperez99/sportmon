# corners_sportmonks_streamlit.py
# ----------------------------------------------------
# UI gráfica en Streamlit para encontrar partidos
# con mercados de "Corners" usando Sportmonks (API v3).
# ----------------------------------------------------

import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://api.sportmonks.com/v3"
FOOTBALL_BASE = f"{BASE_URL}/football"
ODDS_BASE = f"{BASE_URL}/odds"   # para markets (no lleva /football)


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

    # ---------- 1) Markets de corners ----------
    def get_corner_market_ids(self, search_term: str = "corner") -> List[Dict[str, Any]]:
        """
        Busca markets que contengan 'corner'.
        GET /v3/odds/markets/search/{search_term}
        """
        url = f"{ODDS_BASE}/markets/search/{search_term}"
        data = self._get(url)
        markets = data.get("data", []) or []

        corner_markets = []
        for m in markets:
            name = (m.get("name") or "").lower()
            if "corner" in name:
                corner_markets.append(
                    {
                        "id": m.get("id"),
                        "name": m.get("name"),
                        "developer_name": m.get("developer_name"),
                    }
                )
        return corner_markets

    # ---------- 2) Fixtures por fecha ----------
    def get_fixtures_by_date_with_odds(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Fixtures por fecha que tengan odds.
        GET /v3/football/fixtures/date/{date}?filters=havingOdds&include=league;participants
        """
        url = f"{FOOTBALL_BASE}/fixtures/date/{date_str}"
        params = {
            "filters": "havingOdds",
            # En API v3 ya no existe localTeam/visitorTeam -> ahora es participants
            "include": "league;participants",
        }
        data = self._get(url, params=params)
        return data.get("data", []) or []

    # ---------- 3) Fixtures por round ----------
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
        round_data = data.get("data") or {}
        fixtures_wrapper = round_data.get("fixtures") or {}
        fixtures = fixtures_wrapper.get("data", []) or []

        fixtures_with_odds = [fx for fx in fixtures if fx.get("has_odds")]
        return fixtures_with_odds

    # ---------- 4) Odds de corners por fixture ----------
    def get_corner_odds_for_fixture(
        self,
        fixture_id: int,
        market_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """
        Pre-match odds para un fixture en varios markets de corners.
        GET /v3/football/odds/pre-match/fixtures/{fixture_id}/markets/{market_id}
        """
        if not market_ids:
            return []

        all_corner_odds = []
        for m_id in market_ids:
            url = f"{FOOTBALL_BASE}/odds/pre-match/fixtures/{fixture_id}/markets/{m_id}"
            data = self._get(url)
            odds_list = data.get("data", []) or []
            if odds_list:
                all_corner_odds.extend(odds_list)
        return all_corner_odds

    # ---------- 5) DataFrame con partidos que sí tienen corners ----------
    def build_corners_dataframe(
        self,
        fixtures: List[Dict[str, Any]],
        corner_markets: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        filas = []
        market_ids = [m["id"] for m in corner_markets]

        for fx in fixtures:
            fixture_id = fx.get("id")
            starting_at = fx.get("starting_at")
            league = (fx.get("league") or {}).get("data") or {}

            # API v3: equipos vienen en participants
            home_name = None
            away_name = None
            participants = (fx.get("participants") or {}).get("data", []) or []
            for p in participants:
                meta = p.get("meta") or {}
                loc = (meta.get("location") or "").lower()
                name = p.get("name")
                if loc == "home":
                    home_name = name
                elif loc == "away":
                    away_name = name

            league_name = league.get("name")

            try:
                corner_odds = self.get_corner_odds_for_fixture(fixture_id, market_ids)
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

        # 1) Markets de corners
        with st.spinner("Buscando markets relacionados con corners..."):
            corner_markets = finder.get_corner_market_ids()

        if not corner_markets:
            st.warning(
                "No se encontraron markets que contengan 'corner'. "
                "Revisa tu plan o los markets disponibles en Sportmonks."
            )
            return

        st.subheader("Markets de corners detectados")
        st.table(pd.DataFrame(corner_markets))

        # 2) Fixtures según el modo
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

        # 3) Filtrar los que tienen corners
        with st.spinner("Filtrando fixtures que tienen mercados de corners..."):
            df_resultados = finder.build_corners_dataframe(fixtures, corner_markets)

        st.markdown("## ✅ Partidos con apuestas de **corners**")

        if df_resultados.empty:
            st.warning(
                "De los fixtures con odds encontrados, ninguno tiene mercados de corners."
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
