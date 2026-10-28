"""Interactive district dashboard for Rwanda's EICV7 double-exclusion analysis."""

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from lab.data import reliability_labels
from lab.theme import AMBER, apply_theme
from lab.ui import hero, kpi_card, ranked_bars


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "outputs" / "eicv7_district_double_exclusion.csv"
GEOJSON_PATH = ROOT / "data" / "rwanda_districts.geojson"
APK_PATH = ROOT / "deliverables" / "rwanda_inclusion_android.apk"

METRICS = {
    "Double exclusion rate": ("double_exclusion_among_poor", "% of poor households", True),
    "Estimated households with double exclusion": (
        "estimated_double_excluded_poor_households", "Estimated households", False
    ),
    "VUP coverage among poor households": ("vup_coverage_among_poor", "% of poor households", True),
    "Bank or mobile account access": ("financial_access_among_poor", "% of poor households", True),
    "Poverty rate": ("poverty_rate", "% of population", True),
}

COLORS = {
    "navy": "#17365D",
    "teal": "#087E8B",
    "gold": "#D99136",
    "ink": "#1D2935",
    "muted": "#667482",
    "line": "#E3E9EF",
    "surface": "#F5F8FA",
    "white": "#FFFFFF",
}

st.set_page_config(
    page_title="Rwanda Double Exclusion | EICV7",
    page_icon="🇷🇼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      html, body, [class*="css"] { font-family: 'Aptos', 'Segoe UI', Arial, sans-serif; color: #1D2935; }
      .stApp { background: #F7F9FB; }
      [data-testid="stHeader"] { background: rgba(247,249,251,.92); }
      [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E3E9EF; }
      [data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
      .block-container { max-width: 1500px; padding-top: 1.4rem; padding-bottom: 2rem; }
      h1, h2, h3 { font-family: 'Aptos Display', 'Segoe UI', Arial, sans-serif; letter-spacing: -.025em; color: #17365D; }
      h2 { font-size: 1.35rem !important; }
      [data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E3E9EF; border-radius: 14px; padding: 1rem 1.1rem; box-shadow: 0 2px 8px rgba(23,54,93,.035); }
      [data-testid="stMetricLabel"] { color: #667482; font-weight: 600; }
      [data-testid="stMetricValue"] { color: #17365D; font-family: 'Aptos Display', 'Segoe UI', Arial, sans-serif; }
      [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
      div[data-testid="stDataFrame"] { border: 1px solid #E3E9EF; border-radius: 12px; overflow: hidden; }
      .hero { background: linear-gradient(115deg,#17365D 0%,#20536D 68%,#087E8B 100%); border-radius: 18px; padding: 1.6rem 2rem; color: #FFFFFF; margin-bottom: 1.1rem; }
      .hero-kicker { color:#BFE5E4; font-size:.78rem; letter-spacing:.12em; font-weight:700; text-transform:uppercase; }
      .hero h1 { color:#FFFFFF; font-size:2.15rem; margin:.35rem 0 .3rem 0; }
      .hero p { color:#E1EBF0; font-size:1rem; margin:0; }
      .section-note { color:#667482; font-size:.88rem; margin-top:-.4rem; }
      .eyebrow { color:#087E8B; font-size:.76rem; text-transform:uppercase; letter-spacing:.1em; font-weight:700; }
      .small-note { color:#667482; font-size:.82rem; }
      .warning-box { border-left:4px solid #D99136; background:#FFF8ED; padding:.8rem 1rem; border-radius:0 10px 10px 0; color:#594522; }
      .source-footer { border-top:1px solid #E3E9EF; margin-top:2rem; padding-top:.8rem; color:#7B8792; font-size:.78rem; }
      @media (max-width: 760px) { .hero {padding:1.2rem;} .hero h1 {font-size:1.7rem;} }
    </style>
    """,
    unsafe_allow_html=True,
)
apply_theme()


@st.cache_data(show_spinner="Loading EICV7 district estimates…")
def load_data(
    csv_path: str,
    geo_path: str,
    csv_mtime_ns: int,
    geo_mtime_ns: int,
) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(csv_path)
    with open(geo_path, encoding="utf-8") as source:
        shapes = json.load(source)
    return frame, shapes


if not CSV_PATH.exists() or not GEOJSON_PATH.exists():
    st.error("The district output or boundary file is missing. Run `python scripts/analyze_eicv7.py` first.")
    st.stop()

try:
    data, geojson = load_data(
        str(CSV_PATH),
        str(GEOJSON_PATH),
        CSV_PATH.stat().st_mtime_ns,
        GEOJSON_PATH.stat().st_mtime_ns,
    )
except (OSError, ValueError, json.JSONDecodeError) as exc:
    st.error(f"Could not read the dashboard inputs: {exc}")
    st.stop()

required = {
    "district_code", "district", "sample_poor_households", "estimated_poor_households",
    "estimated_poor_population", "estimated_population", "poverty_rate",
    "vup_coverage_among_poor", "financial_access_among_poor",
    "double_exclusion_among_poor", "estimated_double_excluded_poor_households",
    "reliability_flag", "double_exclusion_among_poor_ci_low",
    "double_exclusion_among_poor_ci_high",
}
missing = sorted(required - set(data.columns))
if missing:
    st.error("The district CSV is missing required fields: " + ", ".join(missing))
    st.stop()

data["district_code_str"] = data["district_code"].astype(int).astype(str)
poor_households = data["estimated_poor_households"].sum()
if poor_households <= 0:
    st.error("The district output has no weighted poor households to summarize.")
    st.stop()

national_poverty = data["estimated_poor_population"].sum() / data["estimated_population"].sum()
national_vup = (data["vup_coverage_among_poor"] * data["estimated_poor_households"]).sum() / poor_households
national_finance = (data["financial_access_among_poor"] * data["estimated_poor_households"]).sum() / poor_households
national_double_count = data["estimated_double_excluded_poor_households"].sum()
national_double = national_double_count / poor_households


_measures = list(METRICS)
if st.session_state.get("overview_measure") not in METRICS:
    st.session_state["overview_measure"] = _measures[0]

with st.sidebar:
    st.markdown("<p class='side-label'>Map</p>", unsafe_allow_html=True)
    metric_label = st.selectbox("Map measure", _measures, key="overview_measure")
    st.markdown("<p class='side-label'>Ranking</p>", unsafe_allow_html=True)
    selected_district = st.selectbox(
        "District detail", ["All districts", *sorted(data["district"].unique())]
    )
    sort_order = st.radio("Rank districts", ["Highest first", "Lowest first"], horizontal=True)
    st.markdown("<p class='side-label'>Downloads</p>", unsafe_allow_html=True)
    if st.button("Refresh district estimates", icon=":material/refresh:", width="stretch"):
        load_data.clear()
        st.rerun()
    st.download_button(
        "Download district data (CSV)",
        data=CSV_PATH.read_bytes(),
        file_name="eicv7_district_double_exclusion.csv",
        mime="text/csv",
        width="stretch",
    )
    if APK_PATH.exists():
        st.download_button(
            "Download Android app (APK)",
            data=APK_PATH.read_bytes(),
            file_name=APK_PATH.name,
            mime="application/vnd.android.package-archive",
            width="stretch",
        )
    st.caption("Aggregate district estimates only. Household microdata is not included.")

metric, metric_unit, is_rate = METRICS[metric_label]
map_data = data.copy()
if is_rate:
    map_data[metric] = map_data[metric] * 100

hero(
    "Rwanda · EICV7 2023–24",
    "Poor, uncovered and unbanked.",
    "Where poverty, social protection and financial access intersect across districts.",
    big_number=f"{national_double_count:,.0f}",
    big_label="Doubly excluded households",
    links=[
        ("/Innovation_Lab_Pathways_and_Targeting", "Pathways and targeting"),
        ("/Innovation_Lab_Insights_and_Comparison", "Insights and comparison"),
    ],
)

kpis = st.columns(4, gap="medium")
with kpis[0]:
    kpi_card("Population poverty", f"{national_poverty:.1%}", pct=national_poverty)
with kpis[1]:
    kpi_card("Poor households reached by VUP", f"{national_vup:.1%}", pct=national_vup)
with kpis[2]:
    kpi_card("Poor households with account access", f"{national_finance:.1%}", pct=national_finance)
with kpis[3]:
    kpi_card("Poor households with neither", f"{national_double:.1%}", pct=national_double, accent=True)

leak_col, look_col = st.columns(2, gap="large")
with leak_col:
    st.subheader("Where the leak is")
    st.caption("Each bar is a smaller group of the same poor households.")
    leak = pd.DataFrame(
        {
            "Stage": ["Poor households", "Not reached by VUP", "Neither VUP nor an account"],
            "Households": [
                poor_households,
                (1 - national_vup) * poor_households,
                national_double_count,
            ],
        }
    )
    ranked_bars(leak, "Stage", "Households")
with look_col:
    st.subheader("Districts to look at first")
    st.caption("Highest double-exclusion rate among poor households.")
    look = data.sort_values("double_exclusion_among_poor", ascending=False).head(8)
    ranked_bars(look.assign(Rate=look["double_exclusion_among_poor"] * 100), "district", "Rate", accent=True)

st.markdown("<div class='section-note'>Coverage and overlap measures are calculated among poor households. Poverty uses population weights.</div>", unsafe_allow_html=True)

map_col, rank_col = st.columns([1.25, 0.9], gap="large")
with map_col:
    st.subheader("Geographic pattern")
    st.markdown(f"<div class='section-note'>District distribution · {metric_label.lower()}. Change the measure from Map in the sidebar.</div>", unsafe_allow_html=True)
    # Draw the same GeoJSON coordinates as the Android app and fit the SVG
    # viewBox to Rwanda's actual district bounds. Plotly's geo renderer was
    # leaving the country at world-map scale in some browser sessions.
    feature_values = {
        str(row.district_code): row
        for row in map_data.itertuples(index=False)
    }
    points = []
    for feature in geojson["features"]:
        geometry = feature["geometry"]
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        for polygon in polygons:
            for lon, lat in polygon[0]:
                points.append((lon, lat))
    min_lon = min(point[0] for point in points)
    max_lon = max(point[0] for point in points)
    min_lat = min(point[1] for point in points)
    max_lat = max(point[1] for point in points)
    pad_lon = (max_lon - min_lon) * 0.025
    pad_lat = (max_lat - min_lat) * 0.025
    min_lon, max_lon = min_lon - pad_lon, max_lon + pad_lon
    min_lat, max_lat = min_lat - pad_lat, max_lat + pad_lat

    values = map_data[metric].fillna(0).astype(float)
    max_value = max(float(values.max()), 1e-12)
    scale_stops = ((246, 231, 200), (217, 145, 54), (18, 53, 91))
    paths = []
    for feature in geojson["features"]:
        properties = feature["properties"]
        code = str(properties.get("dist_code", ""))
        row = feature_values.get(code)
        if row is None:
            continue
        fraction = max(0.0, min(1.0, float(getattr(row, metric)) / max_value))
        slot = fraction * (len(scale_stops) - 1)
        left = min(int(slot), len(scale_stops) - 2)
        blend = slot - left
        fill = "#" + "".join(
            f"{round(a + (b - a) * blend):02X}"
            for a, b in zip(scale_stops[left], scale_stops[left + 1])
        )
        geometry = feature["geometry"]
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        commands = []
        for polygon in polygons:
            ring = polygon[0]
            commands.append("M " + " L ".join(
                f"{lon:.6f},{max_lat - lat:.6f}" for lon, lat in ring
            ) + " Z")
        estimate = float(getattr(row, metric))
        formatted = f"{estimate:.1f}%" if is_rate else f"{estimate:,.0f}"
        title = html.escape(
            f"{row.district}: {formatted} · Poor households sampled: {int(row.sample_poor_households):,}"
        )
        selected = selected_district == row.district
        opacity = "1" if selected_district == "All districts" or selected else "0.28"
        outline = "#D99136" if selected else "#FFFFFF"
        outline_width = "2.8" if selected else "1.2"
        paths.append(
            f'<path d="{" ".join(commands)}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{outline}" stroke-width="{outline_width}" '
            f'vector-effect="non-scaling-stroke"><title>{title}</title></path>'
        )
    selected_rows = map_data.loc[map_data["district"].eq(selected_district)]
    if not selected_rows.empty:
        selected_row = selected_rows.iloc[0]
        selected_value = selected_row[metric]
        selected_formatted = f"{selected_value:.1f}%" if is_rate else f"{selected_value:,.0f}"
        selected_label = html.escape(f"{selected_district} · {selected_formatted}")
        badge_width = min(max(len(selected_label) * 0.055 + 0.24, 0.9), max_lon - min_lon - 0.08)
        badge_height = (max_lat - min_lat) * 0.065
        svg_label = (
            f'<g aria-label="Selected district: {selected_label}">'
            f'<rect x="{min_lon + 0.04:.6f}" y="{max_lat - badge_height - 0.04:.6f}" '
            f'width="{badge_width:.6f}" height="{badge_height:.6f}" rx="0.06" fill="#17365D"/>'
            f'<text x="{min_lon + 0.09:.6f}" y="{max_lat - badge_height / 2 - 0.04:.6f}" '
            f'dominant-baseline="middle" fill="#FFFFFF" font-family="Arial,sans-serif" '
            f'font-size="{(max_lat - min_lat) * 0.037:.6f}" font-weight="700">{selected_label}</text>'
            '</g>'
        )
    else:
        svg_label = ""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_lon:.6f} 0 '
        f'{max_lon - min_lon:.6f} {max_lat - min_lat:.6f}" role="img" '
        f'aria-label="Rwanda districts shaded by {html.escape(metric_label)}" '
        'style="display:block;width:100%;height:auto;max-width:100%">'
        + "".join(paths) + svg_label + "</svg>"
    )
    st.markdown(f'<div class="map-card">{svg}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-note" style="text-align:right">Lower '
        f'<span style="display:inline-block;width:110px;height:8px;border-radius:6px;'
        f'background:linear-gradient(90deg,#F6E7C8,#D99136,#12355B);vertical-align:middle"></span> Higher '
        f'· {html.escape(metric_unit)}</div>',
        unsafe_allow_html=True,
    )
    st.caption("Hover over a district for its estimate and sample size. Use District detail in the sidebar to open its profile.")

with rank_col:
    st.subheader("District ranking")
    st.markdown(f"<div class='section-note'>Ranked by {metric_label.lower()}</div>", unsafe_allow_html=True)
    ranked = map_data.sort_values(metric, ascending=(sort_order == "Lowest first")).copy()
    ranked["Estimate"] = ranked[metric].map(lambda v: f"{v:,.1f}%" if is_rate else f"{v:,.0f}")
    ranked["Poor HH sampled"] = ranked["sample_poor_households"].map(lambda v: f"{int(v):,}")
    se_col = "double_exclusion_among_poor_se"
    n_col = "double_exclusion_among_poor_sample_n"
    show_reliability = se_col in data.columns and n_col in data.columns
    if show_reliability:
        labels = reliability_labels(
            data["double_exclusion_among_poor"].to_numpy(dtype=float),
            data[se_col].to_numpy(dtype=float),
            data[n_col].to_numpy(dtype=float),
        )
        ranked["Reliability"] = pd.Series(labels, index=data.index).loc[ranked.index].to_numpy()
        rank_columns = ["district", "Estimate", "Poor HH sampled", "Reliability"]
    else:
        rank_columns = ["district", "Estimate", "Poor HH sampled"]
    rank_view = ranked[rank_columns].rename(columns={"district": "District"})
    st.dataframe(
        rank_view,
        hide_index=True,
        width="stretch",
        height=484,
        alt="District ranking table showing the selected estimate, poor-household sample size, and reliability note.",
        column_config={
            "District": st.column_config.TextColumn("District", width="medium"),
            "Estimate": st.column_config.TextColumn("Estimate", width="small"),
            "Poor HH sampled": st.column_config.TextColumn("Poor HH sampled", width="small"),
            "Reliability": st.column_config.TextColumn("Reliability", width="medium"),
        },
    )
    small = data.loc[data["reliability_flag"].notna() & data["reliability_flag"].ne("")]
    if not small.empty:
        st.caption("Caution: " + "; ".join(small["district"].tolist()) + " have fewer than 50 sampled poor households.")

st.divider()
left, right = st.columns([1.1, 0.9], gap="large")
with left:
    st.subheader("Where the estimated household burden is largest")
    st.markdown("<div class='section-note'>Counts help identify where many households may be affected; they do not indicate an individual household’s status.</div>", unsafe_allow_html=True)
    burden = data.nlargest(10, "estimated_double_excluded_poor_households").sort_values("estimated_double_excluded_poor_households")
    bar = px.bar(
        burden,
        x="estimated_double_excluded_poor_households",
        y="district",
        orientation="h",
        text="estimated_double_excluded_poor_households",
        color_discrete_sequence=[AMBER],
        labels={"estimated_double_excluded_poor_households": "Estimated households", "district": "District"},
    )
    bar.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>Estimated households: %{x:,.0f}<extra></extra>")
    bar.update_layout(
        height=430,
        margin=dict(l=0, r=35, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=11, family="Inter, system-ui, sans-serif", color="#10263D")),
        yaxis=dict(title=None, showgrid=False, zeroline=False, tickfont=dict(size=11, family="Inter, system-ui, sans-serif", color="#10263D")),
        font=dict(family="Inter, system-ui, sans-serif", color="#10263D", size=12),
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(color="#10263D")),
        transition={"duration": 600, "easing": "cubic-in-out"},
    )
    st.plotly_chart(
        bar,
        width="stretch",
        alt="Horizontal bar chart of the ten districts with the largest estimated number of poor households facing double exclusion.",
        config={"displayModeBar": False},
    )

with right:
    st.subheader("Selected district profile")
    district_rows = data if selected_district == "All districts" else data.loc[data["district"].eq(selected_district)]
    if selected_district == "All districts":
        st.markdown("<div class='section-note'>Choose a district in the sidebar to view its weighted profile.</div>", unsafe_allow_html=True)
        highlight = data.nlargest(1, "double_exclusion_among_poor").iloc[0]
        st.metric("Highest double-exclusion rate", highlight["district"], f"{highlight['double_exclusion_among_poor']:.1%} of poor households")
        st.markdown("<div class='warning-box'>A high rate indicates a larger share affected. A high count indicates more households. Use both when planning district follow-up.</div>", unsafe_allow_html=True)
    else:
        row = district_rows.iloc[0]
        st.markdown(f"<div class='eyebrow'>{row['district']} district</div>", unsafe_allow_html=True)
        st.metric("Double exclusion among poor households", f"{row['double_exclusion_among_poor']:.1%}", help="Approximate 95% confidence interval, calculated using the analysis variance method.")
        ci = f"{row['double_exclusion_among_poor_ci_low']:.1%}–{row['double_exclusion_among_poor_ci_high']:.1%}"
        details = pd.DataFrame(
            {
                "Measure": ["Poverty rate", "VUP coverage among poor HH", "Bank/mobile access among poor HH", "Estimated double-excluded HH", "Poor households sampled", "Approx. 95% interval"],
                "Estimate": [f"{row['poverty_rate']:.1%}", f"{row['vup_coverage_among_poor']:.1%}", f"{row['financial_access_among_poor']:.1%}", f"{row['estimated_double_excluded_poor_households']:,.0f}", f"{int(row['sample_poor_households']):,}", ci],
            }
        )
        st.dataframe(
            details,
            hide_index=True,
            width="stretch",
            alt=f"Weighted EICV7 indicator profile for {row['district']} district.",
        )
        reliability_note = row["reliability_flag"]
        if pd.notna(reliability_note) and str(reliability_note).strip():
            st.warning(str(reliability_note))

        credit_reason_fields = {
            "Insufficient collateral": "insufficient_collateral_among_poor_with_recorded_loan_denial",
            "Insufficient income": "insufficient_income_among_poor_with_recorded_loan_denial",
            "Debt-history problems": "debt_history_problems_among_poor_with_recorded_loan_denial",
            "Unclear loan purpose": "unclear_loan_purpose_among_poor_with_recorded_loan_denial",
            "Other stated reason": "other_loan_denial_reason_among_poor_with_recorded_loan_denial",
        }
        vup_reason_fields = {
            "Household had no workers": "vup_ds_reason_no_household_workers_among_poor_direct_support_households",
            "Caring for a person with severe disability": "vup_ds_reason_care_for_severe_disability_among_poor_direct_support_households",
            "Respondent did not know": "vup_ds_reason_dont_know_among_poor_direct_support_households",
        }
        optional_reason_columns = {
            "credit_denial_recorded_among_poor",
            "insufficient_income_among_poor_with_recorded_loan_denial_sample_n",
            "vup_ds_reason_no_household_workers_among_poor_direct_support_households_sample_n",
            *credit_reason_fields.values(),
            *vup_reason_fields.values(),
        }
        if optional_reason_columns.issubset(data.columns):
            with st.expander("Reported credit and VUP reasons", expanded=False):
                st.caption(
                    "EICV7 respondent reports only. These do not explain why a household "
                    "lacks an account or establish VUP eligibility."
                )
                credit_n = int(row["insufficient_income_among_poor_with_recorded_loan_denial_sample_n"])
                vup_n = int(row["vup_ds_reason_no_household_workers_among_poor_direct_support_households_sample_n"])
                st.markdown("**Loan denial recorded among poor households**")
                st.metric(
                    "Poor households with a denied loan recorded",
                    f"{row['credit_denial_recorded_among_poor']:.1%}",
                    help="Household-weighted share of all poor households; this is not a loan-denial rate among applicants.",
                )
                st.caption(f"Reason sample: {credit_n} poor households with a denied loan recorded. Categories may overlap across multiple loan records.")
                credit_reasons = pd.DataFrame(
                    {
                        "Reported reason": list(credit_reason_fields),
                        "Share of this subgroup": [
                            f"{row[field]:.1%}" if pd.notna(row[field]) else "Not estimated"
                            for field in credit_reason_fields.values()
                        ],
                    }
                )
                st.dataframe(
                    credit_reasons,
                    hide_index=True,
                    width="stretch",
                    alt=f"Reported reasons for denied loans among {credit_n} poor households in {row['district']}.",
                )
                st.markdown("**VUP Direct Support enrollment reasons among poor participants**")
                st.caption(f"Respondent sample: {vup_n} poor households reporting Direct Support.")
                vup_reasons = pd.DataFrame(
                    {
                        "Reported reason": list(vup_reason_fields),
                        "Share of this subgroup": [
                            f"{row[field]:.1%}" if pd.notna(row[field]) else "Not estimated"
                            for field in vup_reason_fields.values()
                        ],
                    }
                )
                st.dataframe(
                    vup_reasons,
                    hide_index=True,
                    width="stretch",
                    alt=f"Reported VUP Direct Support enrollment reasons among {vup_n} poor households in {row['district']}.",
                )

with st.expander("Definitions, methods and limitations"):
    st.markdown(
        """
        **Poverty:** EICV7 household poverty classification. District poverty rates use population weights and are checked against NISR's published district benchmarks.

        **VUP coverage:** a positive participation flag in at least one of the five EICV7 VUP modules. It does not measure eligibility.

        **Financial access:** at least one household member reports a bank or mobile-money account. Tontines are retained as a separate measure in the CSV.

        **Double exclusion:** among poor households, neither an observed VUP participation flag nor a reported bank/mobile-money account. All coverage and overlap rates use household survey weights.

        **Uncertainty:** district confidence intervals are approximate and use stratified PSU-cluster ratio linearization with a normal 1.96 multiplier. Districts with fewer than 50 sampled poor households need extra caution.

        **Interpretation:** the cross-sectional, self-reported data are descriptive. They cannot establish program impact, eligibility, the cause of non-coverage, affordability, or active account use. Use these estimates to guide local investigation, not to classify individual households.
        """
    )

st.markdown(
    "<div class='source-footer'>Source: NISR EICV7 2023/24 household microdata and district boundary data. Weighted calculations by the project team. District summaries only; raw microdata is not exposed by this dashboard.</div>",
    unsafe_allow_html=True,
)
