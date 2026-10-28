"""Innovation Lab 1 — pathways, priority ranks, a targeting simulator and the map."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from lab.charts import (
    LISA_COLORS,
    caterpillar,
    choropleth,
    frontier_lines,
    household_funnel,
    pathway_sankey,
    pathway_stacked,
    population_bars,
    priority_components,
    quadrant_scatter,
    rank_intervals,
    rule_comparison,
)
from lab.data import open_lab
from lab.stats import (
    RULE_LABELS,
    RULES,
    add_priority,
    allocate,
    simulate_scenario,
    targeting_frontier,
    weight_sensitivity,
)
from lab import texts
from lab.theme import apply_theme
from lab.ui import (
    banner,
    download_frame,
    footer,
    hero,
    inject_css,
    kpi_strip,
    pathway_ribbon,
    selected_point_label,
    show_chart,
    skeleton_rows,
    tab_open,
)

st.set_page_config(
    page_title="Innovation Lab 1 — Pathways, Priorities and Targeting",
    page_icon="🇷🇼",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()
inject_css()

frame, geojson, national, _model = open_lab()
districts = sorted(frame["district"].unique())
options = ["All districts", *districts]
if "a_district" not in st.session_state:
    st.session_state["a_district"] = "All districts"
pending = st.session_state.pop("a_pending", None)
if pending in options:
    st.session_state["a_district"] = pending

with st.sidebar:
    st.markdown("### Lab controls")
    st.caption("These filters apply only on this page.")
    st.selectbox("Focus district", options, key="a_district")
    with st.expander("Priority index weights", expanded=False):
        weight_rate = st.slider("Double-exclusion rate", 0.0, 1.0, 0.35, 0.05)
        weight_count = st.slider("Double-excluded households", 0.0, 1.0, 0.35, 0.05)
        weight_vup = st.slider("VUP gap", 0.0, 1.0, 0.10, 0.05)
        weight_finance = st.slider("Financial gap", 0.0, 1.0, 0.10, 0.05)
        weight_poverty = st.slider("Poverty rate", 0.0, 1.0, 0.10, 0.05)
        st.caption("Weights are rescaled so they sum to 1.")
    total_poor = float(national["poor_households"])
    step = 1000
    minimum = 1000
    maximum = minimum + int((int(total_poor) - minimum) // step) * step
    default_budget = minimum + int((int(round(total_poor * 0.10)) - minimum) // step) * step
    budget = st.slider(
        "Poor households to reach",
        min_value=minimum,
        max_value=maximum,
        value=default_budget,
        step=step,
        help="How many poor households the scenario tries to reach. The default is about 10% of the national total.",
    )
    st.caption(f"{budget:,.0f} households · {budget / total_poor:.1%} of estimated poor households.")
    rule = st.radio("Allocation rule", RULES, format_func=lambda code: RULE_LABELS[code])
    unit_cost = st.number_input(
        "Unit cost per poor household reached (RWF)",
        min_value=0,
        value=0,
        step=1000,
        help="Optional. Leave at 0 to hide cost. Cost per double-excluded household is this unit cost times the budget, divided by expected double-excluded households.",
    )
    show_unreliable = st.toggle("Show unreliable districts", value=True)
    st.caption(
        "Unreliable means fewer than 30 sampled poor households. "
        f"This file has {national['n_unreliable']} such districts and "
        f"{national['n_caution']} marked interpret with caution."
    )

weights = {
    "de_rate": weight_rate,
    "de_count": weight_count,
    "vup_gap": weight_vup,
    "financial_gap": weight_finance,
    "poverty_rate": weight_poverty,
}
st.session_state["lab_weights"] = weights
view = add_priority(frame, weights)
shown = view if show_unreliable else view.loc[view["reliability_label"] != "Unreliable"].copy()
focus = st.session_state["a_district"]
highlight = st.session_state.get("a_highlight")

hero(
    "Innovation Lab · EICV7 2023–24",
    "Pathways, priorities and targeting",
    "Where poor households miss both VUP and a bank or mobile-money account, and how a district budget could be aimed.",
    big_number=f"{national['double_excluded_households']:,.0f}",
    big_label="Doubly excluded households",
    links=[
        ("/", "Overview"),
        ("/Innovation_Lab_Insights_and_Comparison", "Insights and comparison"),
    ],
)
kpi_strip(
    [
        {
            "label": "Poor households with neither",
            "value": national["double_exclusion_rate"] * 100,
            "kind": "percent",
            "decimals": 1,
            "note": "National, weighted by poor households",
            "meter": national["double_exclusion_rate"] * 100,
            "accent": True,
        },
        {
            "label": "Double-excluded households",
            "value": national["double_excluded_households"],
            "kind": "integer",
            "note": "Estimated count",
            "meter": None,
        },
        {
            "label": "VUP coverage among poor households",
            "value": national["vup_coverage"] * 100,
            "kind": "percent",
            "decimals": 1,
            "note": "National share",
            "meter": national["vup_coverage"] * 100,
        },
        {
            "label": "Account access among poor households",
            "value": national["financial_access"] * 100,
            "kind": "percent",
            "decimals": 1,
            "note": "Bank or mobile money",
            "meter": national["financial_access"] * 100,
        },
    ]
)
st.caption(
    f"Reliability of the double-exclusion rate: {national['n_reliable']} reliable, "
    f"{national['n_caution']} interpret with caution, {national['n_unreliable']} unreliable."
)

pathways_tab, ranks_tab, simulator_tab, map_tab = st.tabs(
    ["Pathways", "Priority and ranks", "Targeting simulator", "Map and spatial"],
    key="lab_a_tabs",
    on_change="rerun",
)


def _scope_counts() -> tuple[str, float, float, float, float, float, float, float, float]:
    if focus == "All districts":
        poor = float(national["poor_households"])
        return (
            "Rwanda",
            poor,
            national["vup_coverage"] * poor,
            float(national["n_vup_and_account"]),
            float(national["n_vup_only"]),
            float(national["n_account_only"]),
            float(national["n_no_vup_no_account"]),
            float(national["population"]),
            float(national["poor_population"]),
        )
    row = view.loc[view["district"] == focus].iloc[0]
    return (
        str(row["district"]),
        float(row["estimated_poor_households"]),
        float(row["vup_coverage_among_poor"] * row["estimated_poor_households"]),
        float(row["n_vup_and_account"]),
        float(row["n_vup_only"]),
        float(row["n_account_only"]),
        float(row["n_no_vup_no_account"]),
        float(row["estimated_population"]),
        float(row["estimated_poor_population"]),
    )


with pathways_tab:
    if tab_open(pathways_tab):
        name, poor, vup_households, both, vup_only, account_only, neither, population, poor_population = _scope_counts()
        shares = {
            "neither VUP nor an account": neither / poor,
            "VUP only": vup_only / poor,
            "an account but no VUP": account_only / poor,
            "both VUP and an account": both / poor,
        }
        largest_name = max(shares, key=shares.get)
        st.subheader(f"Pathways for {name}")
        if national["pathway_warning_districts"]:
            st.warning(
                "Pathway consistency warning: "
                + ", ".join(national["pathway_warning_districts"])
                + ". Details are in the methodology tab of Innovation Lab 2.",
                title="Pathway cells",
            )
        else:
            st.caption("Pathway cells sum to 1 within 0.005 in every district. No cell is below -0.005.")
        pathway_ribbon(
            {
                "Account only": account_only / poor,
                "Neither": neither / poor,
                "VUP and account": both / poor,
                "VUP only": vup_only / poor,
            }
        )
        show_chart(
            pathway_sankey(
                poor_households=poor,
                vup_households=vup_households,
                both=both,
                vup_only=vup_only,
                account_only=account_only,
                neither=neither,
                title=f"Pathway of poor households · {name}",
            ),
            texts.sankey_caption(neither / poor, largest_name, shares[largest_name])
            + " "
            + texts.CAPTIONS["sankey"],
            "Sankey of poor households into VUP or not, then into an account or not.",
        )
        left, right = st.columns(2)
        with left:
            show_chart(
                population_bars(population, poor_population, f"Population · {name}"),
                texts.CAPTIONS["population"],
                "Bar chart of estimated population and estimated poor population.",
            )
        with right:
            show_chart(
                household_funnel(
                    poor,
                    account_only + neither,
                    neither,
                    f"From poor households to double exclusion · {name}",
                ),
                texts.CAPTIONS["funnel"],
                "Funnel from all poor households, to those not reached by VUP, to those with neither VUP nor an account.",
            )
        sort_choice = st.segmented_control(
            "Sort districts by",
            ["Double exclusion", "VUP only", "Account only", "VUP and account"],
            default="Double exclusion",
            key="pathway_sort",
        )
        sort_map = {
            "Double exclusion": "share_no_vup_no_account",
            "VUP only": "share_vup_only",
            "Account only": "share_account_only",
            "VUP and account": "share_vup_and_account",
        }
        sort_column = sort_map.get(sort_choice or "Double exclusion", "share_no_vup_no_account")
        stacked = shown.sort_values(sort_column, ascending=True)
        show_chart(
            pathway_stacked(stacked, "Four pathway states in every district"),
            texts.CAPTIONS["stacked"],
            "Horizontal stacked bar chart of the four pathway states for each district.",
        )
        state = show_chart(
            quadrant_scatter(
                shown,
                float(national["vup_coverage"]),
                float(national["financial_access"]),
                highlight if highlight in set(shown["district"]) else None,
                "VUP coverage and account access among poor households",
            ),
            texts.CAPTIONS["quadrant"],
            "Scatter plot of VUP coverage against account access. Bubble size is estimated poor households and colour is the double-exclusion rate.",
            key="quadrant_select",
        )
        picked = selected_point_label(state)
        if picked and picked != st.session_state.get("a_highlight"):
            st.session_state["a_highlight"] = picked
            st.rerun()
        active = st.session_state.get("a_highlight")
        if active:
            st.caption(f"Highlighted district: {active}.")
            if st.button(f"Focus on {active}", key="focus_highlight"):
                st.session_state["a_pending"] = active
                st.rerun()

with ranks_tab:
    if tab_open(ranks_tab):
        st.subheader("Where the rate is high, and how sure the rank is")
        show_chart(
            caterpillar(
                shown,
                "double_exclusion_among_poor",
                "double_exclusion_among_poor_ci_low",
                "double_exclusion_among_poor_ci_high",
                "double_exclusion_among_poor_sample_n",
                float(national["double_exclusion_rate"]),
                "Double-exclusion rate with 95% intervals",
            ),
            texts.CAPTIONS["caterpillar"] + " Marker colour follows the reliability label: teal reliable, amber caution.",
            "Caterpillar chart of district double-exclusion rates with confidence intervals and a national reference line.",
        )
        show_chart(
            rank_intervals(
                shown,
                "median_rank_rate",
                "rank_rate_p05",
                "rank_rate_p95",
                "Uncertainty of the rate rank",
            ),
            texts.CAPTIONS["ranks"],
            "Lollipop chart of each district's median double-exclusion rank and its 90 percent interval.",
        )
        rank_table = shown.sort_values("median_rank_rate")[
            [
                "district",
                "double_exclusion_among_poor",
                "median_rank_rate",
                "rank_rate_p05",
                "rank_rate_p95",
                "p_top5_rate",
                "p_top10_rate",
                "median_rank_count",
                "p_top5_count",
                "reliability_label",
                "double_exclusion_among_poor_sample_n",
            ]
        ].rename(
            columns={
                "district": "District",
                "double_exclusion_among_poor": "Double-exclusion rate",
                "median_rank_rate": "Median rate rank",
                "rank_rate_p05": "Rate rank, 5th percentile",
                "rank_rate_p95": "Rate rank, 95th percentile",
                "p_top5_rate": "P(top 5 by rate)",
                "p_top10_rate": "P(top 10 by rate)",
                "median_rank_count": "Median count rank",
                "p_top5_count": "P(top 5 by count)",
                "reliability_label": "Reliability",
                "double_exclusion_among_poor_sample_n": "Sample of poor households",
            }
        )
        st.dataframe(
            rank_table,
            hide_index=True,
            width="stretch",
            alt="Table of median ranks, 90 percent intervals, and the probability of a top-5 or top-10 place.",
        )
        show_chart(
            priority_components(shown, "Priority index by component"),
            texts.CAPTIONS["priority"],
            "Stacked bar chart of each district's priority-index components.",
        )
        sensitivity = weight_sensitivity(
            view["double_exclusion_among_poor"].to_numpy(),
            view["estimated_double_excluded_poor_households"].to_numpy(),
            view["vup_gap"].to_numpy(),
            view["financial_gap"].to_numpy(),
            view["poverty_rate"].to_numpy(),
            view["district"].to_numpy(),
            weights,
        )
        st.dataframe(
            sensitivity,
            hide_index=True,
            width="stretch",
            alt="Sensitivity of the top 10 when each priority weight changes by 50 percent.",
        )
        st.caption(texts.CAPTIONS["sensitivity"])
        download_left, download_right = st.columns(2)
        with download_left:
            download_frame(
                "Download rank table (CSV)",
                rank_table,
                "double_exclusion_rank_uncertainty.csv",
                key="download_ranks",
            )
        with download_right:
            priority_table = shown.sort_values("priority_rank")[
                [
                    "district",
                    "priority_index",
                    "priority_rank",
                    "contrib_de_rate",
                    "contrib_de_count",
                    "contrib_vup_gap",
                    "contrib_financial_gap",
                    "contrib_poverty_rate",
                    "reliability_label",
                ]
            ]
            download_frame(
                "Download priority table (CSV)",
                priority_table,
                "double_exclusion_priority_index.csv",
                key="download_priority",
            )

with simulator_tab:
    if tab_open(simulator_tab):
        banner(
            "Illustrative simulation on district-level estimates; assumes random selection of "
            "poor households within a district. It does not identify individual households."
        )
        st.caption(texts.RULE_NOTES[rule])
        hold = st.empty()
        hold.markdown(skeleton_rows(3), unsafe_allow_html=True)
        rate = view["double_exclusion_among_poor"].to_numpy()
        poor_households = view["estimated_poor_households"].to_numpy()
        scenario = simulate_scenario(
            poor_households,
            rate,
            view["double_exclusion_among_poor_se"].to_numpy(),
            float(budget),
            rule,
            priority=view["priority_index"].to_numpy(),
            reliability=view["reliability_label"].to_numpy(),
            unit_cost=float(unit_cost) if unit_cost > 0 else None,
        )
        baseline = allocate(poor_households, rate, float(budget), "R0")
        baseline_reached = float(np.sum(baseline * rate))
        hold.empty()
        cards = [
            {
                "label": "Double-excluded households reached",
                "value": scenario.expected_de,
                "kind": "integer",
                "note": f"90% interval {scenario.de_p05:,.0f}–{scenario.de_p95:,.0f}",
                "meter": None,
            },
            {
                "label": "Share of all double-excluded households",
                "value": scenario.recall * 100,
                "kind": "percent",
                "decimals": 1,
                "note": "Recall",
                "meter": scenario.recall * 100,
            },
            {
                "label": "Precision",
                "value": scenario.precision * 100,
                "kind": "percent",
                "decimals": 1,
                "note": "Double-excluded households per household reached",
                "meter": scenario.precision * 100,
            },
        ]
        if scenario.cost_per_de is not None:
            cards.append(
                {
                    "label": "Cost per double-excluded household",
                    "value": scenario.cost_per_de,
                    "kind": "integer",
                    "note": "RWF, using the unit cost in the sidebar",
                    "meter": None,
                }
            )
        kpi_strip(cards, columns=len(cards), pulse=True)
        st.markdown(texts.simulator_contrast(rule, scenario.expected_de, baseline_reached))
        allocated = view.copy()
        allocated["allocation"] = scenario.allocation
        allocated["expected_de"] = scenario.allocation * rate
        allocated["de_p05"] = scenario.district_p05
        allocated["de_p95"] = scenario.district_p95
        show_chart(
            choropleth(
                allocated,
                geojson,
                "allocation",
                f"Households allocated · {RULE_LABELS[rule]}",
                tickformat=",.0f",
                colorbar="Households",
                highlight=focus if focus != "All districts" else highlight,
            ),
            texts.CAPTIONS["allocation"],
            "Map of how many poor households each district would be allocated under the selected rule.",
        )
        allocation_table = allocated.loc[allocated["allocation"] > 0].sort_values("allocation", ascending=False)
        display_allocation = pd.DataFrame(
            {
                "District": allocation_table["district"],
                "Poor households": allocation_table["estimated_poor_households"].round(0),
                "Allocated households": allocation_table["allocation"].round(0),
                "Expected double-excluded households": allocation_table["expected_de"].round(0),
                "90% low": allocation_table["de_p05"].round(0),
                "90% high": allocation_table["de_p95"].round(0),
                "Reliability": allocation_table["reliability_label"],
            }
        )
        st.dataframe(
            display_allocation,
            hide_index=True,
            width="stretch",
            alt="Allocation table with expected double-excluded households and the 90 percent interval.",
        )
        comparison_rows = []
        for code in RULES:
            allocation = allocate(
                poor_households,
                rate,
                float(budget),
                code,
                view["priority_index"].to_numpy(),
                view["reliability_label"].to_numpy(),
            )
            expected = float(np.sum(allocation * rate))
            spent = float(allocation.sum())
            comparison_rows.append(
                {
                    "rule": code,
                    "recall": expected / scenario.total_de if scenario.total_de else 0,
                    "precision": expected / spent if spent else 0,
                    "expected_de": expected,
                }
            )
        comparison = pd.DataFrame(comparison_rows)
        show_chart(
            rule_comparison(comparison, "Recall and precision at this budget"),
            texts.CAPTIONS["rules"],
            "Grouped bar chart comparing recall and precision for rules R0 to R4 at the selected budget.",
        )
        frontier = targeting_frontier(
            poor_households,
            rate,
            view["priority_index"].to_numpy(),
            view["reliability_label"].to_numpy(),
        )
        show_chart(
            frontier_lines(frontier, "Recall as the budget grows"),
            texts.CAPTIONS["frontier"],
            "Line chart of recall against budget share for five allocation rules.",
        )
        download_frame(
            "Download scenario (CSV)",
            display_allocation,
            "targeting_scenario.csv",
            key="download_scenario",
        )

with map_tab:
    if tab_open(map_tab):
        st.subheader("Map and spatial pattern")
        st.caption("Exploratory, 30 districts. Neighbours are based on district centroids, not a cadastral boundary test.")
        measure_labels = {
            "Double-exclusion rate": ("double_exclusion_among_poor", True, ".1%", "Rate"),
            "Double-excluded households": ("estimated_double_excluded_poor_households", True, ",.0f", "Households"),
            "VUP gap": ("vup_gap", True, ".1%", "Gap"),
            "Financial gap": ("financial_gap", True, ".1%", "Gap"),
            "Poverty rate": ("poverty_rate", True, ".1%", "Rate"),
            "Priority index": ("priority_index", True, None, "Index"),
            "EB-stabilised double-exclusion rate": ("d_eb", True, ".1%", "Rate"),
            "LISA cluster": ("lisa_label", False, None, ""),
        }
        measure = st.selectbox("Map measure", list(measure_labels))
        use_stabilised = st.toggle("Use the stabilised rate instead of the direct rate", value=False)
        column, continuous, tickformat, colorbar = measure_labels[measure]
        if use_stabilised and column == "double_exclusion_among_poor":
            column = "d_eb"
            colorbar = "Stabilised rate"
        show_chart(
            choropleth(
                view,
                geojson,
                column,
                measure,
                continuous=continuous,
                color_map=LISA_COLORS if column == "lisa_label" else None,
                tickformat=tickformat,
                colorbar=colorbar,
                highlight=focus if focus != "All districts" else highlight,
            ),
            texts.CAPTIONS["map"],
            f"Choropleth of Rwandan districts shaded by {measure}.",
        )
        st.metric("Moran's I", f"{_model['moran_i']:.2f}", help="Global spatial autocorrelation of the double-exclusion rate.")
        st.caption(texts.moran_reading(float(_model["moran_i"]), float(_model["moran_p"])) + " " + texts.CAPTIONS["moran"])
        hotspots = view.loc[view["lisa_significant"], ["district", "lisa_quadrant", "lisa_p", "double_exclusion_among_poor"]]
        if hotspots.empty:
            st.caption("No district has a local Moran quadrant that passes the 5% permutation threshold.")
        else:
            st.dataframe(
                hotspots.rename(
                    columns={
                        "district": "District",
                        "lisa_quadrant": "Quadrant",
                        "lisa_p": "Pseudo p-value",
                        "double_exclusion_among_poor": "Double-exclusion rate",
                    }
                ),
                hide_index=True,
                width="stretch",
                alt="Districts whose local Moran quadrant is significant in the permutation test.",
            )

footer()
