"""Streamlit dashboard for the EICV7 district double-exclusion analysis."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "outputs" / "eicv7_district_double_exclusion.csv"
GEOJSON_PATH = ROOT / "data" / "rwanda_districts.geojson"

METRICS = {
    "Double exclusion among poor households": (
        "double_exclusion_among_poor", "Percent of poor households"
    ),
    "Estimated number of double-excluded poor households": (
        "estimated_double_excluded_poor_households", "Estimated households"
    ),
    "VUP coverage among poor households": (
        "vup_coverage_among_poor", "Percent of poor households"
    ),
    "Bank or mobile account access among poor households": (
        "financial_access_among_poor", "Percent of poor households"
    ),
    "District poverty rate": ("poverty_rate", "Percent of population")
}


st.set_page_config(page_title="Rwanda Double Exclusion", layout="wide")
st.title("Double exclusion in Rwanda")
st.caption("District estimates from EICV7 2023-2024. Select a measure to explore the geography and ranking.")

if not CSV_PATH.exists() or not GEOJSON_PATH.exists():
    st.error("Required aggregate CSV or district boundary GeoJSON is missing. Run the analysis script first.")
    st.stop()

data = pd.read_csv(CSV_PATH)
data["district_code_str"] = data["district_code"].astype(int).astype(str)
with GEOJSON_PATH.open(encoding="utf-8") as source:
    geojson = json.load(source)

metric_label = st.selectbox("Map and rank by", list(METRICS))
metric, unit = METRICS[metric_label]
metric_data = data.copy()
if unit.startswith("Percent"):
    metric_data[metric] = metric_data[metric] * 100

national_poverty = data["estimated_poor_population"].sum() / data["estimated_population"].sum()
poor_households = data["estimated_poor_households"].sum()
national_vup = (data["vup_coverage_among_poor"] * data["estimated_poor_households"]).sum() / poor_households
national_finance = (data["financial_access_among_poor"] * data["estimated_poor_households"]).sum() / poor_households
national_double = data["estimated_double_excluded_poor_households"].sum() / poor_households

summary = st.columns(4)
summary[0].metric("Population poverty rate", f"{national_poverty:.1%}")
summary[1].metric("VUP coverage among poor households", f"{national_vup:.1%}")
summary[2].metric("Bank or mobile account access among poor households", f"{national_finance:.1%}")
summary[3].metric("Poor households with double exclusion", f"{national_double:.1%}")

map_col, summary_col = st.columns([1.35, 1])
with map_col:
    figure = px.choropleth(
        metric_data,
        geojson=geojson,
        locations="district_code_str",
        featureidkey="properties.dist_code",
        color=metric,
        hover_name="district",
        hover_data={
            metric: ":.1f" if unit.startswith("Percent") else ":,.0f",
            "sample_poor_households": True,
            "double_exclusion_among_poor": ":.1%",
            "vup_coverage_among_poor": ":.1%",
            "financial_access_among_poor": ":.1%",
            "district_code_str": False,
        },
        color_continuous_scale="YlOrRd",
        labels={metric: unit},
        title=metric_label,
    )
    figure.update_geos(fitbounds="locations", visible=False, bgcolor="white")
    figure.update_layout(margin={"r": 5, "t": 48, "l": 5, "b": 5}, height=620)
    st.plotly_chart(figure, use_container_width=True)

with summary_col:
    ranked = metric_data.sort_values(metric, ascending=False)
    display = ranked[["district", metric, "sample_poor_households", "reliability_flag"]].copy()
    display[metric] = display[metric].map(lambda value: f"{value:,.1f}" + ("%" if unit.startswith("Percent") else ""))
    display.columns = ["District", unit, "Poor households sampled", "Reliability note"]
    st.subheader("District ranking")
    st.dataframe(display, hide_index=True, use_container_width=True, height=620)

top = data.sort_values("estimated_double_excluded_poor_households", ascending=False).head(5)
st.subheader("Largest estimated double-exclusion burden")
cards = st.columns(5)
for col, row in zip(cards, top.itertuples(index=False)):
    col.metric(row.district, f"{row.estimated_double_excluded_poor_households:,.0f}",
               f"{row.double_exclusion_among_poor:.1%} of poor households")

with st.expander("Definitions and interpretation"):
    st.markdown(
        """
        - Poverty is the EICV7 household poverty classification. The district poverty rate uses the population weight.
        - VUP coverage means a positive participation flag in at least one of the five VUP modules.
        - Financial access means at least one household member has a bank or mobile money account. Tontines are shown separately in the downloadable data.
        - Double exclusion is measured among poor households with neither a VUP participation flag nor bank/mobile account access.
        - Rates use survey weights. Approximate 95% confidence intervals are available in the aggregate CSV. Districts with fewer than 50 sampled poor households carry a reliability note.
        - The analysis measures observed coverage; it does not establish VUP eligibility or causal impact.
        """
    )

st.download_button(
    "Download district estimates",
    data=CSV_PATH.read_bytes(),
    file_name="eicv7_district_double_exclusion.csv",
    mime="text/csv",
)
