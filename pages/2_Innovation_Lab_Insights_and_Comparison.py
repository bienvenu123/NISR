"""Innovation Lab 2 — district insights, twins, barriers, alerts and methods."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lab.charts import (
    CLUSTER_PALETTE,
    caterpillar,
    choropleth,
    cluster_heatmap,
    correlation_heatmap,
    eb_dumbbell,
    gap_bars,
    mini_pathway,
    parallel_coordinates,
    radar,
    reason_bars,
    typology_scatter,
)
from lab.data import LOAN_REASONS, VUP_REASONS, open_lab
from lab.stats import add_priority, indicator_gap
from lab import texts
from lab.theme import apply_theme
from lab.ui import (
    alert_feed,
    copy_panel,
    download_text,
    footer,
    hero,
    inject_css,
    kpi_strip,
    llm_available,
    maybe_rewrite_brief,
    profile_heading,
    show_chart,
    tab_open,
)

st.set_page_config(
    page_title="Innovation Lab 2 — Insights, Comparison and Alerts",
    page_icon="🇷🇼",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()
inject_css()

frame, geojson, national, model = open_lab()
view = add_priority(frame, st.session_state.get("lab_weights"))
districts = sorted(view["district"].unique())
if "b_district" not in st.session_state:
    st.session_state["b_district"] = districts[0]

with st.sidebar:
    st.markdown("### Lab controls")
    st.caption("District choices on this page sit in each tab. Priority weights, if you set them on Lab 1, are reused here.")
    st.selectbox("Focus district", districts, key="b_district")

focus_row = view.loc[view["district"].eq(st.session_state["b_district"])].iloc[0]
hero(
    "Innovation Lab · EICV7 2023–24",
    "Insights, comparison and alerts",
    "Read a district against the national picture, its nearest neighbours, and the limits of the estimates.",
    big_number=f"{float(focus_row['double_exclusion_among_poor']):.1%}",
    big_label=f"{focus_row['district']} double exclusion",
    links=[
        ("/", "Overview"),
        ("/Innovation_Lab_Pathways_and_Targeting", "Pathways and targeting"),
    ],
)

explorer_tab, twins_tab, barriers_tab, alerts_tab, methods_tab = st.tabs(
    ["District explorer", "Twins and typology", "Barriers", "Alerts and brief", "Methodology"],
    key="lab_b_tabs",
    on_change="rerun",
)


def _delta(value: float, reference: float, *, higher_is_worse: bool) -> tuple[str, str]:
    gap = (value - reference) * 100
    if abs(gap) < 0.05:
        return "In line with national", "#3E4C59"
    word = "above national" if gap > 0 else "below national"
    worse = gap > 0 if higher_is_worse else gap < 0
    return f"{abs(gap):.1f} pp {word}", ("#6B4A12" if worse else "#0B4F57")


def _profile(row: pd.Series) -> None:
    profile_heading(
        str(row["district"]),
        str(row["province"]),
        str(row["reliability_label"]),
        str(row["cluster_name"]),
    )
    exclusion_note, exclusion_color = _delta(
        float(row["double_exclusion_among_poor"]),
        float(national["double_exclusion_rate"]),
        higher_is_worse=True,
    )
    vup_note, vup_color = _delta(
        float(row["vup_coverage_among_poor"]),
        float(national["vup_coverage"]),
        higher_is_worse=False,
    )
    finance_note, finance_color = _delta(
        float(row["financial_access_among_poor"]),
        float(national["financial_access"]),
        higher_is_worse=False,
    )
    kpi_strip(
        [
            {
                "label": "Double exclusion",
                "value": float(row["double_exclusion_among_poor"]) * 100,
                "kind": "percent",
                "decimals": 1,
                "note": exclusion_note
                + f" · {row['double_exclusion_among_poor_ci_low']:.1%}–{row['double_exclusion_among_poor_ci_high']:.1%}",
                "note_color": exclusion_color,
                "meter": float(row["double_exclusion_among_poor"]) * 100,
                "accent": True,
            },
            {
                "label": "VUP coverage",
                "value": float(row["vup_coverage_among_poor"]) * 100,
                "kind": "percent",
                "decimals": 1,
                "note": vup_note,
                "note_color": vup_color,
                "meter": float(row["vup_coverage_among_poor"]) * 100,
            },
            {
                "label": "Account access",
                "value": float(row["financial_access_among_poor"]) * 100,
                "kind": "percent",
                "decimals": 1,
                "note": finance_note,
                "note_color": finance_color,
                "meter": float(row["financial_access_among_poor"]) * 100,
            },
            {
                "label": "Double-excluded households",
                "value": float(row["estimated_double_excluded_poor_households"]),
                "kind": "integer",
                "note": f"Sample of poor households {int(row['double_exclusion_among_poor_sample_n'])}",
                "meter": None,
            },
        ],
        columns=2,
    )
    st.markdown(texts.district_insight(row, national))
    shares = {column: float(row[column]) for column, _label, _color in (
        ("share_no_vup_no_account", "", ""),
        ("share_vup_only", "", ""),
        ("share_account_only", "", ""),
        ("share_vup_and_account", "", ""),
    )}
    show_chart(
        mini_pathway(shares, f"Pathway · {row['district']}"),
        texts.CAPTIONS["stacked"],
        f"Stacked bar of the four pathway states for {row['district']}.",
    )


def _radar_values(row: pd.Series) -> list[float]:
    return [
        float(row[column]) * 100
        for column in (
            "poverty_rate",
            "extreme_poverty_rate",
            "vup_coverage_among_poor",
            "financial_access_among_poor",
            "double_exclusion_among_poor",
            "tontine_participation_among_poor",
        )
    ]


RADAR_AXES = [
    "Poverty",
    "Extreme poverty",
    "VUP coverage",
    "Account access",
    "Double exclusion",
    "Tontine",
]


with explorer_tab:
    if tab_open(explorer_tab):
        focus = st.session_state["b_district"]
        compare_options = ["None", *[name for name in districts if name != focus]]
        if st.session_state.get("b_compare") not in compare_options:
            st.session_state["b_compare"] = "None"
        compare = st.selectbox(
            "Compare with",
            compare_options,
            key="b_compare",
        )
        row = view.loc[view["district"] == focus].iloc[0]
        twin = view.loc[view["district"] == row["better_twin"]].iloc[0]
        national_radar = [
            float(national[key]) * 100
            for key in (
                "poverty_rate",
                "extreme_poverty_rate",
                "vup_coverage",
                "financial_access",
                "double_exclusion_rate",
                "tontine",
            )
        ]
        if compare == "None":
            _profile(row)
            show_chart(
                radar(
                    [
                        (str(row["district"]), _radar_values(row)),
                        ("National", national_radar),
                        (f"Better twin · {twin['district']}", _radar_values(twin)),
                    ],
                    RADAR_AXES,
                    f"{row['district']} against the national profile and {twin['district']}",
                ),
                texts.CAPTIONS["radar"],
                f"Radar chart comparing {row['district']} with the national rates and its better-performing twin.",
            )
        else:
            other = view.loc[view["district"] == compare].iloc[0]
            left, right = st.columns(2)
            with left:
                _profile(row)
            with right:
                _profile(other)
            show_chart(
                radar(
                    [
                        (str(row["district"]), _radar_values(row)),
                        (str(other["district"]), _radar_values(other)),
                        ("National", national_radar),
                    ],
                    RADAR_AXES,
                    f"{row['district']} and {other['district']}",
                ),
                texts.CAPTIONS["radar"],
                f"Radar chart comparing {row['district']} and {other['district']} with national rates.",
            )
        show_chart(
            eb_dumbbell(view, "Direct rate and stabilised rate"),
            texts.CAPTIONS["dumbbell"],
            "Dumbbell chart joining each district's direct double-exclusion rate to its empirical-Bayes rate.",
        )

with twins_tab:
    if tab_open(twins_tab):
        st.subheader("District typology")
        st.caption(
            f"KMeans chose {model['k']} clusters (silhouette {model['silhouette']:.2f}). "
            "Names describe the cluster centroid, not a league table."
        )
        show_chart(
            typology_scatter(
                view,
                tuple(model["pca_variance"]),
                "Districts on the first two principal components",
            ),
            texts.CAPTIONS["typology"],
            "Scatter plot of districts on two principal components, coloured by cluster.",
        )
        show_chart(
            cluster_heatmap(model["profile_z"], "Cluster profiles, standardised"),
            texts.CAPTIONS["heatmap"],
            "Heatmap of cluster means on standardised indicators.",
        )
        counts = view["cluster_name"].value_counts()
        profile = model["profile_raw"].reset_index().rename(columns={"cluster": "Typology"})
        profile.insert(1, "Districts", profile["Typology"].map(counts))
        profile["Suggested lever"] = profile["Typology"].map(texts.lever_for)
        pretty = profile.rename(
            columns={
                "poverty_rate": "Mean poverty rate",
                "vup_gap": "Mean VUP gap",
                "financial_gap": "Mean financial gap",
                "double_exclusion_among_poor": "Mean double exclusion",
                "log_poor_households": "Mean log poor households",
            }
        )
        st.dataframe(
            pretty,
            hide_index=True,
            width="stretch",
            alt="Cluster profile table with the recommended lever for each typology.",
        )
        cluster_colors = {
            name: CLUSTER_PALETTE[index % len(CLUSTER_PALETTE)]
            for index, name in enumerate(dict.fromkeys(view["cluster_name"]))
        }
        show_chart(
            choropleth(
                view,
                geojson,
                "cluster_name",
                "Typology map",
                continuous=False,
                color_map=cluster_colors,
                highlight=st.session_state["b_district"],
            ),
            "What this means: neighbouring colours are a typology, not a ranking of need.",
            "Map of districts coloured by their typology cluster.",
        )
        st.subheader("Twin finder")
        anchor_name = st.session_state["b_district"]
        anchor = view.loc[view["district"] == anchor_name].iloc[0]
        twins = [str(anchor["twin_1"]), str(anchor["twin_2"]), str(anchor["twin_3"])]
        st.markdown(
            f"**{anchor_name}** is closest to {', '.join(twins)}. "
            f"The better-performing twin on double exclusion is **{anchor['better_twin']}** "
            f"({float(anchor['better_twin_d']):.1%})."
        )
        st.caption(texts.lever_for(str(anchor["cluster_name"])))
        gaps = indicator_gap(view, anchor_name, str(anchor["better_twin"]))
        show_chart(
            gap_bars(gaps, f"{anchor_name} minus {anchor['better_twin']}"),
            texts.CAPTIONS["twins"],
            f"Bar chart of indicator gaps between {anchor_name} and {anchor['better_twin']}.",
        )
        correlation_columns = [
            ("poverty_rate", "Poverty"),
            ("extreme_poverty_rate", "Extreme poverty"),
            ("vup_coverage_among_poor", "VUP coverage"),
            ("financial_access_among_poor", "Account access"),
            ("tontine_participation_among_poor", "Tontine"),
            ("double_exclusion_among_poor", "Double exclusion"),
            ("log_poor_households", "Log poor households"),
        ]
        show_chart(
            correlation_heatmap(
                view,
                [column for column, _label in correlation_columns],
                [label for _column, label in correlation_columns],
                "Correlations across the 30 districts",
            ),
            texts.CAPTIONS["correlation"],
            "Heatmap of Pearson correlations between district indicators.",
        )
        default_lines = [anchor_name, *twins]
        chosen = st.multiselect(
            "Districts on the parallel-coordinates chart",
            districts,
            default=default_lines,
            key="parallel_districts",
        )
        if chosen:
            show_chart(
                parallel_coordinates(
                    view.loc[view["district"].isin(chosen)],
                    [
                        ("poverty_rate", "Poverty %", True),
                        ("vup_coverage_among_poor", "VUP %", True),
                        ("financial_access_among_poor", "Account %", True),
                        ("double_exclusion_among_poor", "Double exclusion %", True),
                        ("tontine_participation_among_poor", "Tontine %", True),
                    ],
                    "Selected district profiles",
                ),
                texts.CAPTIONS["parallel"],
                "Parallel-coordinates chart of the selected districts.",
            )
        else:
            st.caption("Select at least one district to draw the parallel-coordinates chart.")

with barriers_tab:
    if tab_open(barriers_tab):
        st.subheader("Recorded reasons")
        st.markdown(texts.CAPTIONS["reasons"])
        loan_items = [item for item in national["loan_reasons"] if item["share"] is not None]
        vup_items = [item for item in national["vup_reasons"] if item["share"] is not None]
        if loan_items:
            show_chart(
                reason_bars(loan_items, "Loan-denial reasons, pooled recorded cases"),
                "What this means: each bar is weighted by the number of recorded cases. No district is plotted on its own because every district sample is below 30.",
                "Bar chart of pooled loan-denial reasons among poor households with a recorded denial.",
            )
        else:
            st.info("Loan-denial reasons are n too small, including the pooled sample.", title="Loan-denial reasons")
        if vup_items:
            show_chart(
                reason_bars(vup_items, "VUP direct-support reasons, pooled recorded cases"),
                "What this means: these shares are among poor households who reported a direct-support reason, not among all poor households.",
                "Bar chart of pooled VUP direct-support reasons.",
            )
        else:
            st.info("VUP direct-support reasons are n too small, including the pooled sample.", title="VUP reasons")
        sample_rows = []
        for label, column in (*LOAN_REASONS, *VUP_REASONS):
            sample = view[f"{column}_sample_n"]
            sample_rows.append(
                {
                    "Indicator": label,
                    "Districts with n ≥ 30": int((sample >= 30).sum()),
                    "Smallest district n": int(sample.min()),
                    "Largest district n": int(sample.max()),
                    "Pooled recorded cases": int(sample.sum()),
                    "District display": "n too small",
                }
            )
        st.dataframe(
            pd.DataFrame(sample_rows),
            hide_index=True,
            width="stretch",
            alt="Sample sizes for loan-denial and VUP direct-support reason indicators.",
        )
        st.caption("Every district is below the display threshold of 30 for these reason shares, so the rates are not plotted district by district.")
        show_chart(
            caterpillar(
                view,
                "credit_denial_recorded_among_poor",
                "credit_denial_recorded_among_poor_ci_low",
                "credit_denial_recorded_among_poor_ci_high",
                "credit_denial_recorded_among_poor_sample_n",
                float(national["credit_denial_rate"]),
                "Credit denial recorded among poor households",
                check_sample=True,
            ),
            texts.CAPTIONS["credit"],
            "Caterpillar chart of the share of poor households with a denied loan recorded, with confidence intervals.",
        )

with alerts_tab:
    if tab_open(alerts_tab):
        st.subheader("Alert feed")
        st.caption(texts.CAPTIONS["alerts"])
        severity_choice = st.pills(
            "Severity",
            ["High", "Medium", "Info"],
            selection_mode="multi",
            default=["High", "Medium", "Info"],
            key="alert_severity",
        )
        selected = {item.lower() for item in (severity_choice or [])}
        district_filter = st.multiselect("Districts", ["All districts", *districts], default=["All districts"])
        alerts = model["alerts"]
        if selected:
            alerts = [alert for alert in alerts if alert["severity"] in selected]
        if district_filter and "All districts" not in district_filter:
            alerts = [alert for alert in alerts if alert["district"] in district_filter]
        alert_feed(alerts)
        st.subheader("Auto brief")
        scope = st.selectbox("Brief for", ["National", *districts], key="brief_scope")
        if scope == "National":
            brief = texts.national_brief(view.to_dict(orient="records"), national, model)
            stem = "national"
        else:
            brief = texts.district_brief(view.loc[view["district"] == scope].iloc[0], national)
            stem = scope.lower().replace(" ", "_")
        use_model = False
        if llm_available():
            use_model = st.checkbox(
                "Rewrite the brief with an external model",
                value=False,
                help="Off by default. Sends only the numbers in the template. Any error keeps the template.",
            )
        brief, rewritten = maybe_rewrite_brief(brief, use_model)
        if rewritten:
            st.warning("AI-generated, verify before use.", title="Language-model rewrite")
        st.text_area("Brief text", brief, height=280, key="brief_text")
        copy_panel(brief)
        download_row = st.columns(2)
        with download_row[0]:
            download_text("Download .txt", brief, f"{stem}_brief.txt", "text/plain", key="brief_txt")
        with download_row[1]:
            markdown = f"# Double exclusion brief — {scope}\n\n{brief}\n\n---\nIllustrative decision-support text computed from EICV7 district aggregates. Not for individual eligibility decisions.\n"
            download_text("Download .md", markdown, f"{stem}_brief.md", "text/markdown", key="brief_md")

with methods_tab:
    if tab_open(methods_tab):
        st.subheader("Methodology")
        if national["pathway_warning_districts"]:
            st.warning(
                "Pathway consistency warning for: " + ", ".join(national["pathway_warning_districts"]),
                title="Pathway check",
            )
        else:
            st.success(
                "All 30 districts pass the pathway check: the four cells sum to 1 within 0.005 and no cell is below -0.005.",
                title="Pathway check",
            )
        for title, body in texts.methodology_sections(list(national["pathway_warning_districts"])):
            with st.expander(title, expanded=title == "Definitions"):
                st.markdown(body)
        validation = pd.DataFrame(
            {
                "District": view["district"],
                "Estimated poverty (%)": (view["poverty_rate"] * 100).round(2),
                "Published NISR poverty (%)": view["published_poverty_rate_pct"],
                "Difference (percentage points)": view["poverty_rate_difference_pp"],
            }
        )
        st.markdown("**Poverty rate against the published NISR district rate**")
        st.dataframe(
            validation,
            hide_index=True,
            width="stretch",
            alt="Comparison of the estimated district poverty rate with the published NISR rate.",
        )
        st.caption(
            "The difference column is poverty_rate_difference_pp from the district file: "
            "estimated percent minus the published percent."
        )

footer()
