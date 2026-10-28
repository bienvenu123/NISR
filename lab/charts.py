"""Plotly figures for the Innovation Lab. Every series comes from the caller."""

from __future__ import annotations

from typing import Any

import copy

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .data import require_plottable
from .theme import AMBER, INK, LIGHT_BLUE, MUTED, NAVY, SEQUENTIAL, TEAL
from .theme import plotly_font

FONT = "Inter, system-ui, sans-serif"
LINE = "#E6E0D4"
SKY = LIGHT_BLUE
BLUE = "#0072B2"
PLUM = "#CC79A7"
WINE = "#882255"

PATHWAYS: tuple[tuple[str, str, str], ...] = (
    ("share_no_vup_no_account", "Neither VUP nor account", AMBER),
    ("share_vup_only", "VUP only", LIGHT_BLUE),
    ("share_account_only", "Account only", TEAL),
    ("share_vup_and_account", "VUP and account", NAVY),
)

RELIABILITY_COLORS = {
    "Reliable": TEAL,
    "Interpret with caution": "#5B6B7B",
    "Unreliable": WINE,
}

DIVERGING = [[0.0, BLUE], [0.5, "#F7F9FB"], [1.0, NAVY]]
CLUSTER_PALETTE = [NAVY, TEAL, LIGHT_BLUE, BLUE, PLUM]
LISA_COLORS = {
    "HH": NAVY,
    "LL": SKY,
    "HL": "#5B6B7B",
    "LH": PLUM,
    "Not significant": "#D5DDE3",
}

_DISPLAY_GEO: dict[int, dict[str, Any]] = {}


def _layout(fig: go.Figure, title: str, height: int, *, cartesian: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK, family=FONT), x=0, xanchor="left"),
        font=plotly_font(),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=8, r=8, t=48, b=8),
        transition={"duration": 600, "easing": "cubic-in-out"},
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(color=INK, family=FONT, size=12)),
        legend=dict(orientation="h", yanchor="top", y=-0.18, x=0, font=dict(size=11, family=FONT, color=INK)),
    )
    tick = dict(size=11, family=FONT, color=INK)
    if cartesian:
        fig.update_xaxes(showgrid=False, zeroline=False, tickfont=tick)
        fig.update_yaxes(showgrid=False, zeroline=False, tickfont=tick)
    return fig


def _thin_ring(ring: list, step: int) -> list:
    if len(ring) <= step * 2:
        return ring
    thinned = ring[::step]
    if thinned[0] != ring[0]:
        thinned.insert(0, ring[0])
    if thinned[-1] != ring[-1]:
        thinned.append(ring[-1])
    return thinned


def _thin_geometry(geometry: dict[str, Any], step: int) -> dict[str, Any]:
    if geometry["type"] == "Polygon":
        coordinates = [_thin_ring(ring, step) for ring in geometry["coordinates"]]
        return {"type": "Polygon", "coordinates": coordinates}
    if geometry["type"] == "MultiPolygon":
        coordinates = [
            [_thin_ring(ring, step) for ring in polygon] for polygon in geometry["coordinates"]
        ]
        return {"type": "MultiPolygon", "coordinates": coordinates}
    raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def display_geojson(geojson: dict[str, Any], step: int = 12) -> dict[str, Any]:
    """Thinned copy for drawing. Codes and names are unchanged; the join still uses the source file."""
    key = id(geojson)
    cached = _DISPLAY_GEO.get(key)
    if cached is not None:
        return cached
    features = [
        {
            "type": "Feature",
            "properties": feature["properties"],
            "geometry": _thin_geometry(feature["geometry"], step),
        }
        for feature in geojson["features"]
    ]
    simplified = {"type": "FeatureCollection", "features": features}
    _DISPLAY_GEO[key] = simplified
    return simplified


def pathway_sankey(
    *,
    poor_households: float,
    vup_households: float,
    both: float,
    vup_only: float,
    account_only: float,
    neither: float,
    title: str,
) -> go.Figure:
    """Poor households split into VUP / no VUP, then into the four pathway states."""
    no_vup = max(poor_households - vup_households, 0.0)
    links = [
        (0, 1, vup_households),
        (0, 2, no_vup),
        (1, 3, both),
        (1, 4, vup_only),
        (2, 5, account_only),
        (2, 6, neither),
    ]
    links = [link for link in links if link[2] > 1]
    labels = [
        "Poor households",
        "VUP",
        "No VUP",
        "VUP and account",
        "VUP only",
        "Account only",
        "Neither",
    ]
    node_colors = [TEAL, TEAL, AMBER, SKY, AMBER, TEAL, NAVY]
    link_colors = ["rgba(8,126,139,0.35)", "rgba(217,145,54,0.35)", "rgba(86,180,233,0.45)", "rgba(217,145,54,0.45)", "rgba(8,126,139,0.45)", "rgba(23,54,93,0.45)"]
    percents = [value / poor_households if poor_households else 0 for _source, _target, value in links]
    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=18,
                    thickness=16,
                    label=labels,
                    color=node_colors,
                    line=dict(color="#FFFFFF", width=0.4),
                    hovertemplate="%{label}<br>%{value:,.0f} households<extra></extra>",
                ),
                link=dict(
                    source=[item[0] for item in links],
                    target=[item[1] for item in links],
                    value=[item[2] for item in links],
                    color=link_colors[: len(links)],
                    customdata=percents,
                    hovertemplate="%{source.label} → %{target.label}<br>%{value:,.0f} households<br>%{customdata:.1%} of poor households<extra></extra>",
                ),
            )
        ]
    )
    return _layout(fig, title, 460, cartesian=False)


def household_funnel(poor: float, without_vup: float, double_excluded: float, title: str) -> go.Figure:
    """Three household counts: all poor, not reached by VUP, then double excluded."""
    labels = ["Poor households", "Not reached by VUP", "No VUP and no account"]
    values = [poor, without_vup, double_excluded]
    text = [f"{value:,.0f}" for value in values]
    fig = go.Figure(
        go.Funnel(
            y=labels,
            x=values,
            text=text,
            textinfo="text",
            marker={"color": [TEAL, AMBER, NAVY]},
            connector={"line": {"color": LINE, "width": 1}},
            hovertemplate="%{y}<br>%{x:,.0f} households<extra></extra>",
        )
    )
    return _layout(fig, title, 380, cartesian=False)


def population_bars(population: float, poor_population: float, title: str) -> go.Figure:
    """People, not households: the population step before the household funnel."""
    fig = go.Figure(
        go.Bar(
            x=["Estimated population", "Estimated poor population"],
            y=[population, poor_population],
            marker_color=[TEAL, NAVY],
            text=[f"{population:,.0f}", f"{poor_population:,.0f}"],
            textposition="outside",
            hovertemplate="%{x}<br>%{y:,.0f} people<extra></extra>",
        )
    )
    fig.update_yaxes(title_text="People")
    return _layout(fig, title, 380)


def pathway_stacked(frame: pd.DataFrame, title: str) -> go.Figure:
    """100% stacked bars. ``frame`` must already be in the desired sort order."""
    fig = go.Figure()
    for column, label, color in PATHWAYS:
        fig.add_trace(
            go.Bar(
                name=label,
                y=frame["district"],
                x=frame[column],
                orientation="h",
                marker_color=color,
                customdata=np.stack([frame["district"], frame[column] * 100], axis=1),
                hovertemplate="%{customdata[0]}<br>" + label + ": %{customdata[1]:.1f}%<extra></extra>",
            )
        )
    fig.update_layout(barmode="stack", bargap=0.25)
    fig.update_xaxes(title_text="Share of poor households", tickformat=".0%", range=[0, 1])
    return _layout(fig, title, max(420, 22 * len(frame) + 80))


def quadrant_scatter(
    frame: pd.DataFrame,
    national_vup: float,
    national_financial: float,
    highlight: str | None,
    title: str,
) -> go.Figure:
    """VUP coverage against account access. Colour is the double-exclusion rate."""
    poor = frame["estimated_poor_households"].to_numpy(dtype=float)
    span = max(float(poor.max() - poor.min()), 1.0)
    size = 14 + 34 * (poor - poor.min()) / span
    custom = np.stack(
        [
            frame["district"],
            frame["double_exclusion_among_poor_ci_low"],
            frame["double_exclusion_among_poor_ci_high"],
            frame["double_exclusion_among_poor_sample_n"],
        ],
        axis=1,
    )
    fig = go.Figure(
        go.Scatter(
            x=frame["vup_coverage_among_poor"],
            y=frame["financial_access_among_poor"],
            mode="markers",
            marker=dict(
                size=size,
                color=frame["double_exclusion_among_poor"],
                colorscale=SEQUENTIAL,
                showscale=True,
                colorbar=dict(title="Double exclusion", tickformat=".0%"),
                line=dict(width=1, color="#FFFFFF"),
            ),
            customdata=custom,
            hovertemplate=(
                "%{customdata[0]}<br>VUP %{x:.1%}<br>Account %{y:.1%}"
                "<br>Double exclusion %{marker.color:.1%}"
                "<br>95% interval %{customdata[1]:.1%}–%{customdata[2]:.1%}"
                "<br>Sample n %{customdata[3]:.0f}<extra></extra>"
            ),
            name="Districts",
        )
    )
    if highlight and highlight in set(frame["district"]):
        row = frame.loc[frame["district"] == highlight].iloc[0]
        fig.add_trace(
            go.Scatter(
                x=[row["vup_coverage_among_poor"]],
                y=[row["financial_access_among_poor"]],
                mode="markers",
                marker=dict(size=18, color=AMBER, symbol="diamond", line=dict(width=1, color=NAVY)),
                name=highlight,
                hovertemplate=f"{highlight}<extra></extra>",
            )
        )
    fig.add_vline(x=national_vup, line_dash="dot", line_color=MUTED)
    fig.add_hline(y=national_financial, line_dash="dot", line_color=MUTED)
    fig.add_annotation(x=national_vup / 2, y=(national_financial + 1) / 2, text="Not covered, banked", showarrow=False, font=dict(color=MUTED, size=11))
    fig.add_annotation(x=(national_vup + 1) / 2, y=(national_financial + 1) / 2, text="Covered and banked", showarrow=False, font=dict(color=MUTED, size=11))
    fig.add_annotation(x=national_vup / 2, y=national_financial / 2, text="Not covered, not banked", showarrow=False, font=dict(color=MUTED, size=11))
    fig.add_annotation(x=(national_vup + 1) / 2, y=national_financial / 2, text="Covered, not banked", showarrow=False, font=dict(color=MUTED, size=11))
    fig.update_xaxes(title_text="VUP coverage among poor households", tickformat=".0%", range=[-0.02, 1.02])
    fig.update_yaxes(title_text="Bank or mobile-money access among poor households", tickformat=".0%", range=[-0.02, 1.05])
    return _layout(fig, title, 520)


def caterpillar(
    frame: pd.DataFrame,
    value_column: str,
    low_column: str,
    high_column: str,
    sample_column: str,
    national: float | None,
    title: str,
    *,
    as_percent: bool = True,
    check_sample: bool = False,
) -> go.Figure:
    """Dots with 95% intervals. Optional national reference line."""
    if check_sample:
        require_plottable(frame[sample_column], what=title)
    ordered = frame.sort_values(value_column, ascending=True)
    value = ordered[value_column].to_numpy(dtype=float)
    low = ordered[low_column].to_numpy(dtype=float)
    high = ordered[high_column].to_numpy(dtype=float)
    plus = np.where(np.isfinite(high), np.maximum(high - value, 0), 0)
    minus = np.where(np.isfinite(low), np.maximum(value - low, 0), 0)
    if value_column == "double_exclusion_among_poor":
        colors = [AMBER] * len(ordered)
    else:
        colors = [RELIABILITY_COLORS.get(str(label), TEAL) for label in ordered["reliability_label"]]
    fig = go.Figure(
        go.Scatter(
            x=value,
            y=ordered["district"],
            mode="markers",
            marker=dict(color=colors, size=11, line=dict(width=1, color="#FFFFFF")),
            error_x=dict(type="data", array=plus, arrayminus=minus, color=MUTED, thickness=4, width=0),
            customdata=np.stack(
                [ordered["district"], ordered[sample_column], low, high, ordered["reliability_label"]],
                axis=1,
            ),
            hovertemplate=(
                "%{customdata[0]}<br>Estimate %{x:.1%}<br>95% CI %{customdata[2]:.1%}–%{customdata[3]:.1%}"
                "<br>Sample n %{customdata[1]:.0f}<br>%{customdata[4]}<extra></extra>"
                if as_percent
                else "%{customdata[0]}<br>Estimate %{x:,.3f}<br>95% CI %{customdata[2]:,.3f}–%{customdata[3]:,.3f}"
                "<br>Sample n %{customdata[1]:.0f}<br>%{customdata[4]}<extra></extra>"
            ),
            name="District estimate",
        )
    )
    if national is not None:
        fig.add_vline(x=national, line_color=NAVY, line_width=1.5, annotation_text="National", annotation_position="top")
    fig.update_xaxes(title_text="Share" if as_percent else "Estimate", tickformat=".0%" if as_percent else None)
    return _layout(fig, title, max(420, 22 * len(ordered) + 80))


def rank_intervals(frame: pd.DataFrame, median: str, low: str, high: str, title: str) -> go.Figure:
    """Median rank with a 90% interval. Rank 1 is the highest rate or count."""
    ordered = frame.sort_values(median, ascending=False)
    med = ordered[median].to_numpy(dtype=float)
    p05 = ordered[low].to_numpy(dtype=float)
    p95 = ordered[high].to_numpy(dtype=float)
    fig = go.Figure(
        go.Scatter(
            x=med,
            y=ordered["district"],
            mode="markers",
            marker=dict(color=TEAL, size=9),
            error_x=dict(
                type="data",
                array=np.maximum(p95 - med, 0),
                arrayminus=np.maximum(med - p05, 0),
                color=NAVY,
                thickness=1.4,
            ),
            customdata=np.stack([ordered["district"], p05, p95], axis=1),
            hovertemplate="%{customdata[0]}<br>Median rank %{x:.1f}<br>90% interval %{customdata[1]:.1f}–%{customdata[2]:.1f}<extra></extra>",
            name="Median rank",
        )
    )
    fig.update_xaxes(title_text="Rank (1 = highest)", autorange="reversed")
    return _layout(fig, title, max(420, 22 * len(ordered) + 80))


def priority_components(frame: pd.DataFrame, title: str) -> go.Figure:
    """Weighted z-score pieces. Positives and negatives stack from zero."""
    ordered = frame.sort_values("priority_index", ascending=True)
    pieces = [
        ("contrib_de_rate", "Double-exclusion rate", NAVY),
        ("contrib_de_count", "Double-excluded households", TEAL),
        ("contrib_vup_gap", "VUP gap", LIGHT_BLUE),
        ("contrib_financial_gap", "Financial gap", BLUE),
        ("contrib_poverty_rate", "Poverty rate", PLUM),
    ]
    fig = go.Figure()
    for column, label, color in pieces:
        fig.add_trace(
            go.Bar(
                name=label,
                y=ordered["district"],
                x=ordered[column],
                orientation="h",
                marker_color=color,
                hovertemplate="%{y}<br>" + label + ": %{x:.2f}<extra></extra>",
            )
        )
    fig.update_layout(barmode="relative")
    fig.update_xaxes(title_text="Contribution to the priority index")
    return _layout(fig, title, max(460, 22 * len(ordered) + 120))


def rule_comparison(summary: pd.DataFrame, title: str) -> go.Figure:
    """Grouped bars of recall and precision at one budget."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Recall", x=summary["rule"], y=summary["recall"], marker_color=NAVY, hovertemplate="%{x}<br>Recall %{y:.1%}<extra></extra>"))
    fig.add_trace(go.Bar(name="Precision", x=summary["rule"], y=summary["precision"], marker_color=TEAL, hovertemplate="%{x}<br>Precision %{y:.1%}<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Share", tickformat=".0%")
    return _layout(fig, title, 380)


def frontier_lines(frontier: pd.DataFrame, title: str) -> go.Figure:
    """Recall against budget share for R0–R4."""
    colors = {"R0": MUTED, "R1": NAVY, "R2": TEAL, "R3": LIGHT_BLUE, "R4": PLUM}
    fig = go.Figure()
    for rule, part in frontier.groupby("rule", sort=False):
        fig.add_trace(
            go.Scatter(
                name=str(rule),
                x=part["budget_share"],
                y=part["recall"],
                mode="lines+markers",
                line=dict(color=colors.get(str(rule), NAVY), width=2),
                hovertemplate=str(rule) + "<br>Budget %{x:.0%}<br>Recall %{y:.1%}<extra></extra>",
            )
        )
    fig.update_xaxes(title_text="Budget as a share of poor households", tickformat=".0%")
    fig.update_yaxes(title_text="Share of double-excluded households reached", tickformat=".0%")
    return _layout(fig, title, 420)


def choropleth(
    frame: pd.DataFrame,
    geojson: dict[str, Any],
    column: str,
    title: str,
    *,
    continuous: bool = True,
    color_map: dict[str, str] | None = None,
    tickformat: str | None = None,
    colorbar: str = "",
    highlight: str | None = None,
) -> go.Figure:
    """District choropleth. ``featureidkey`` is properties.dist_code, matched to district_code_str."""
    shapes = copy.deepcopy(display_geojson(geojson))
    if continuous:
        shown = _format_values(frame[column], tickformat)
        fig = go.Figure(
            go.Choropleth(
                geojson=shapes,
                locations=frame["district_code_str"],
                z=frame[column],
                featureidkey="properties.dist_code",
                colorscale=SEQUENTIAL,
                marker_line_color="#FFFFFF",
                marker_line_width=0.6,
                colorbar=dict(title=colorbar, tickformat=tickformat or ""),
                customdata=np.stack([frame["district"], shown], axis=1),
                hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
                name="",
            )
        )
    else:
        palette = color_map or {}
        labels = list(dict.fromkeys(frame[column].astype(str)))
        codes = {label: index for index, label in enumerate(labels)}
        fig = go.Figure(
            go.Choropleth(
                geojson=shapes,
                locations=frame["district_code_str"],
                z=frame[column].astype(str).map(codes),
                featureidkey="properties.dist_code",
                colorscale=_discrete_scale(labels, palette),
                marker_line_color="#FFFFFF",
                marker_line_width=0.6,
                showscale=False,
                customdata=np.stack([frame["district"], frame[column].astype(str)], axis=1),
                hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
                name="",
            )
        )
    if highlight and highlight in set(frame["district"]) and "lon" in frame.columns:
        row = frame.loc[frame["district"] == highlight].iloc[0]
        fig.add_trace(
            go.Scattergeo(
                lon=[row["lon"]],
                lat=[row["lat"]],
                mode="markers",
                marker=dict(size=11, color=AMBER, line=dict(width=1, color=NAVY)),
                name=highlight,
                hovertemplate=f"{highlight}<extra></extra>",
            )
        )
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(margin=dict(l=0, r=0, t=56, b=0))
    _layout(fig, title, 520, cartesian=False)
    fig.update_layout(legend=dict(orientation="h", y=-0.05))
    return fig


def _format_values(series: pd.Series, tickformat: str | None) -> list[str]:
    formatted: list[str] = []
    for value in series:
        if pd.isna(value):
            formatted.append("n too small")
        elif tickformat == ".1%":
            formatted.append(f"{float(value):.1%}")
        elif tickformat == ",.0f":
            formatted.append(f"{float(value):,.0f}")
        else:
            formatted.append(f"{float(value):.2f}")
    return formatted


def _discrete_scale(labels: list[str], palette: dict[str, str]) -> list:
    if not labels:
        return SEQUENTIAL
    colors = [
        palette.get(label, CLUSTER_PALETTE[index % len(CLUSTER_PALETTE)])
        for index, label in enumerate(labels)
    ]
    scale = []
    for index, color in enumerate(colors):
        start = index / len(colors)
        end = (index + 1) / len(colors)
        scale.append([start, color])
        scale.append([end, color])
    return scale


def eb_dumbbell(frame: pd.DataFrame, title: str) -> go.Figure:
    """Direct rate joined to the stabilised rate. Amber marks a shift above 2 percentage points."""
    ordered = frame.sort_values("double_exclusion_among_poor", ascending=True)
    fig = go.Figure()
    for row in ordered.itertuples(index=False):
        color = AMBER if abs(float(row.eb_shift_pp)) > 2 else "#C5D0D8"
        fig.add_trace(
            go.Scatter(
                x=[row.double_exclusion_among_poor, row.d_eb],
                y=[row.district, row.district],
                mode="lines",
                line=dict(color=color, width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=ordered["double_exclusion_among_poor"],
            y=ordered["district"],
            mode="markers",
            name="Direct",
            marker=dict(color=NAVY, size=8),
            hovertemplate="%{y}<br>Direct %{x:.1%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ordered["d_eb"],
            y=ordered["district"],
            mode="markers",
            name="Stabilised",
            marker=dict(color=TEAL, size=8),
            customdata=np.stack([ordered["shrink"], ordered["eb_shift_pp"]], axis=1),
            hovertemplate="%{y}<br>Stabilised %{x:.1%}<br>Shrink factor %{customdata[0]:.2f}<br>Shift %{customdata[1]:+.1f} pp<extra></extra>",
        )
    )
    fig.update_xaxes(title_text="Double-exclusion rate", tickformat=".0%")
    return _layout(fig, title, max(460, 22 * len(ordered) + 80))


def typology_scatter(frame: pd.DataFrame, variance: tuple[float, float], title: str) -> go.Figure:
    """PCA plane coloured by cluster name."""
    fig = go.Figure()
    for index, (name, part) in enumerate(frame.groupby("cluster_name", sort=False)):
        fig.add_trace(
            go.Scatter(
                x=part["pca_x"],
                y=part["pca_y"],
                mode="markers+text",
                text=part["district"],
                textposition="top center",
                name=str(name),
                marker=dict(size=12, color=CLUSTER_PALETTE[index % len(CLUSTER_PALETTE)]),
                customdata=np.stack([part["district"]], axis=1),
                hovertemplate="%{customdata[0]}<br>" + str(name) + "<extra></extra>",
            )
        )
    fig.update_xaxes(title_text=f"Component 1 ({variance[0]:.0%} of variance)")
    fig.update_yaxes(title_text=f"Component 2 ({variance[1]:.0%} of variance)")
    return _layout(fig, title, 520)


def cluster_heatmap(profile_z: pd.DataFrame, title: str) -> go.Figure:
    """Clusters by standardised indicator. Zero is the 30-district average."""
    labels = {
        "poverty_rate": "Poverty rate",
        "vup_gap": "VUP gap",
        "financial_gap": "Financial gap",
        "double_exclusion_among_poor": "Double exclusion",
        "log_poor_households": "Log poor households",
    }
    matrix = profile_z.rename(columns=labels)
    fig = go.Figure(
        go.Heatmap(
            z=matrix.to_numpy(),
            x=list(matrix.columns),
            y=list(matrix.index),
            colorscale=DIVERGING,
            zmid=0,
            colorbar=dict(title="z-score"),
            hovertemplate="%{y}<br>%{x}<br>%{z:.2f}<extra></extra>",
        )
    )
    return _layout(fig, title, 360, cartesian=False)


def gap_bars(gaps: pd.DataFrame, title: str) -> go.Figure:
    """This district minus the twin. Shares are shown in percentage points."""
    display = gaps.copy()
    values = [
        (float(row["Gap (this − twin)"]) * 100 if row["Share"] else float(row["Gap (this − twin)"]))
        for _index, row in display.iterrows()
    ]
    colors = [NAVY if value >= 0 else TEAL for value in values]
    fig = go.Figure(
        go.Bar(
            y=display["Indicator"],
            x=values,
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}<br>Gap %{x:.2f}<extra></extra>",
        )
    )
    fig.update_xaxes(title_text="Gap (percentage points for rates, households for counts)")
    return _layout(fig, title, 420)


def radar(series: list[tuple[str, list[float]]], categories: list[str], title: str) -> go.Figure:
    """Rates on a 0–100% axis so districts, the national line and a twin share a scale."""
    colors = [NAVY, TEAL, AMBER]
    fig = go.Figure()
    for index, (name, values) in enumerate(series):
        closed = list(values) + [values[0]]
        cats = categories + [categories[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=closed,
                theta=cats,
                name=name,
                fill="toself",
                line=dict(color=colors[index % len(colors)]),
                hovertemplate="%{theta}<br>%{r:.1f}%<extra>" + name + "</extra>",
            )
        )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%")),
        showlegend=True,
    )
    return _layout(fig, title, 460, cartesian=False)


def correlation_heatmap(frame: pd.DataFrame, columns: list[str], labels: list[str], title: str) -> go.Figure:
    """Pearson correlations across districts."""
    matrix = frame[columns].corr(method="pearson")
    fig = go.Figure(
        go.Heatmap(
            z=matrix.to_numpy(),
            x=labels,
            y=labels,
            zmin=-1,
            zmax=1,
            colorscale=DIVERGING,
            colorbar=dict(title="r"),
            text=np.round(matrix.to_numpy(), 2),
            texttemplate="%{text:.2f}",
            hovertemplate="%{y} and %{x}<br>r = %{z:.2f}<extra></extra>",
        )
    )
    return _layout(fig, title, 480, cartesian=False)


def parallel_coordinates(frame: pd.DataFrame, columns: list[tuple[str, str, bool]], title: str) -> go.Figure:
    """One line per district. Rate columns are drawn as percentages."""
    dimensions = []
    for column, label, is_share in columns:
        values = frame[column].to_numpy(dtype=float)
        if is_share:
            values = values * 100
        dimensions.append(dict(label=label, values=values))
    fig = go.Figure(
        data=go.Parcoords(
            line=dict(
                color=frame["double_exclusion_among_poor"],
                colorscale=SEQUENTIAL,
                showscale=True,
                colorbar=dict(title="Double exclusion", tickformat=".0%"),
            ),
            dimensions=dimensions,
            labelangle=-20,
        )
    )
    return _layout(fig, title, 460, cartesian=False)


def reason_bars(items: list[dict[str, Any]], title: str) -> go.Figure:
    """National pooled reason shares. Items with a null share are omitted by the caller."""
    labels = [item["label"] for item in items]
    shares = [float(item["share"]) for item in items]
    samples = [int(item["sample_n"]) for item in items]
    fig = go.Figure(
        go.Bar(
            y=labels,
            x=shares,
            orientation="h",
            marker_color=TEAL,
            customdata=samples,
            hovertemplate="%{y}<br>%{x:.1%} of recorded cases<br>Pooled n %{customdata}<extra></extra>",
        )
    )
    fig.update_xaxes(title_text="Share of recorded cases", tickformat=".0%")
    return _layout(fig, title, 360)


def mini_pathway(shares: dict[str, float], title: str) -> go.Figure:
    """One stacked bar for a district or the national pathway."""
    fig = go.Figure()
    for column, label, color in PATHWAYS:
        fig.add_trace(
            go.Bar(
                name=label,
                y=["Poor households"],
                x=[shares[column]],
                orientation="h",
                marker_color=color,
                hovertemplate=label + ": %{x:.1%}<extra></extra>",
            )
        )
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat=".0%", range=[0, 1], title_text="Share of poor households")
    return _layout(fig, title, 220)
