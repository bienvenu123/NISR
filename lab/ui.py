"""Theme, motion and small interface helpers for the Innovation Lab pages."""

from __future__ import annotations

import html
import json
import re
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from .theme import apply_theme

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}

_CSS = """
<style>
  html, body, [class*="css"] {
    font-family: Aptos, "Segoe UI", Arial, sans-serif;
    color: #1D2935;
  }
  .stApp { background: #F7F9FB; overflow-x: hidden; }
  [data-testid="stHeader"] { background: rgba(247,249,251,.92); }
  [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E3E9EF; }
  .block-container { max-width: 1500px; padding-top: 1rem; padding-bottom: 2rem; }
  h1, h2, h3 {
    font-family: "Aptos Display", "Segoe UI", Arial, sans-serif;
    letter-spacing: -.025em;
    color: #17365D;
  }
  p, li, label, .stCaption, [data-testid="stCaptionContainer"] { color: #3E4C59; }
  .stButton > button, .stDownloadButton > button, [data-testid="stBaseButton-secondary"],
  [data-testid="stBaseButton-primary"], [role="tab"], button[data-baseweb="tab"] {
    min-height: 44px; border-radius: 12px;
  }
  [data-testid="stElementToolbar"] button { min-height: 44px; min-width: 44px; }
  button:active { transform: scale(0.98); }
  div[data-baseweb="select"] > div, [data-baseweb="slider"] { min-height: 44px; }
  [data-baseweb="tab-list"] { flex-wrap: wrap; gap: 4px; }
  [data-baseweb="tab"] { min-height: 44px; }
  [data-baseweb="tab-highlight"] {
    background-color: #087E8B !important;
    height: 3px !important;
    transition: left 220ms ease, width 220ms ease;
  }
  [data-testid="stMetricValue"], .stDataFrame, .kpi-num { font-variant-numeric: tabular-nums; }
  div[data-testid="stDataFrame"] { border: 1px solid #E3E9EF; border-radius: 12px; overflow: hidden; }
  [data-testid="stPlotlyChart"] { max-width: 100%; }
  .lab-hero {
    background: linear-gradient(115deg, #17365D 0%, #20536D 52%, #087E8B 100%);
    background-size: 200% 200%;
    animation: lab-shimmer 8s ease-in-out infinite;
    border-radius: 16px;
    padding: 24px 32px;
    color: #FFFFFF;
    margin: 0 0 16px 0;
    box-shadow: 0 8px 24px rgba(23,54,93,.12);
  }
  .lab-hero .hero-kicker {
    color: #E7F6F5;
    font-size: .78rem;
    letter-spacing: .12em;
    font-weight: 700;
    text-transform: uppercase;
  }
  .lab-hero h1 {
    color: #FFFFFF;
    font-size: 2.05rem;
    margin: 8px 0;
    animation: lab-fade-up .7s ease both;
  }
  .lab-hero p { color: #E1EBF0; font-size: 1rem; margin: 0; animation: lab-fade-up .7s ease .08s both; }
  .source-footer {
    border-top: 1px solid #E3E9EF;
    margin-top: 32px;
    padding-top: 16px;
    color: #3E4C59;
    font-size: .82rem;
    line-height: 1.45;
  }
  .lab-banner {
    border-left: 4px solid #D99136;
    background: #FFF8ED;
    color: #5C3B08;
    padding: 12px 16px;
    border-radius: 0 12px 12px 0;
    margin: 8px 0 16px 0;
  }
  .badge {
    display: inline-block;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: .78rem;
    font-weight: 700;
    margin-right: 8px;
    line-height: 1.4;
  }
  .badge-ok { background: #E5F4F4; color: #0B4F57; }
  .badge-warn { background: #FFF4E5; color: #6B4A12; }
  .badge-bad { background: #F6E8EE; color: #6E2344; }
  .badge-info { background: #E8EEF5; color: #17365D; }
  .alert-card {
    background: #FFFFFF;
    border: 1px solid #E3E9EF;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 8px;
    box-shadow: 0 2px 8px rgba(23,54,93,.04);
  }
  .alert-card strong { color: #17365D; }
  .chip-high { background: #FFF4E5; color: #6B4A12; }
  .chip-medium { background: #E5F4F4; color: #0B4F57; }
  .chip-info { background: #E8EEF5; color: #17365D; }
  .kpi-row { display: grid; gap: 8px; margin: 8px 0 16px 0; }
  .kpi-row.cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .kpi-row.cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .kpi-row.cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kpi-card {
    background: #FFFFFF; border: 1px solid #E3E9EF; border-radius: 12px;
    padding: 16px; box-shadow: 0 2px 8px rgba(23,54,93,.05);
    animation: lab-fade-up .6s ease both; min-height: 104px;
    transition: transform .18s ease, box-shadow .18s ease;
  }
  .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(23,54,93,.12); }
  .kpi-card.pulse { animation: lab-fade-up .6s ease both, lab-pulse .8s ease .15s 1; }
  .kpi-label { color: #3E4C59; font-size: .78rem; font-weight: 700; }
  .kpi-num { color: #17365D; font-size: 1.55rem; font-weight: 700; margin: 4px 0; font-variant-numeric: tabular-nums; }
  .kpi-note { font-size: .82rem; min-height: 1.2em; }
  .kpi-meter { height: 4px; background: #E3E9EF; border-radius: 999px; margin-top: 8px; overflow: hidden; }
  .kpi-meter > span { display: block; height: 100%; width: 0; background: #087E8B; animation: lab-meter 1.2s cubic-bezier(.22,1,.36,1) forwards; }
  @keyframes lab-meter { to { width: var(--meter); } }
  @keyframes lab-pulse {
    0% { box-shadow: 0 0 0 0 rgba(8,126,139,.35); }
    100% { box-shadow: 0 0 0 12px rgba(8,126,139,0); }
  }
  .js-plotly-plot .barlayer .point {
    transform-box: fill-box;
    animation: lab-fade-up .7s cubic-bezier(.22,1,.36,1) both;
  }
  .js-plotly-plot .sankey { animation: lab-fade .8s ease both; }
  @keyframes lab-shimmer {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }
  @keyframes lab-fade-up {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: none; }
  }
  @keyframes lab-fade { from { opacity: 0; } to { opacity: 1; } }
  @media (max-width: 760px) {
    .lab-hero { padding: 16px; }
    .kpi-row.cols-4, .kpi-row.cols-3, .kpi-row.cols-2 { grid-template-columns: 1fr; }
    .lab-hero h1 { font-size: 1.55rem; }
    .block-container { padding-left: 1rem; padding-right: 1rem; }
  }
  @media (prefers-reduced-motion: reduce) {
    .lab-hero, .lab-hero h1, .lab-hero p,
    .kpi-card, .kpi-card.pulse, .kpi-meter > span,
    .js-plotly-plot .barlayer .point, .js-plotly-plot .sankey,
    button {
      animation: none !important;
      transition: none !important;
    }
    button:active, .kpi-card:hover { transform: none; }
    .kpi-meter > span { width: var(--meter); }
  }
</style>
"""


def inject_css() -> None:
    """Inject the shared lab stylesheet once per run."""
    apply_theme()


def _count_target(value: object) -> tuple[float | None, str, int]:
    """Split a display value into a number, suffix, and decimal places."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        decimals = 0 if float(number).is_integer() else 1
        return number, "", decimals
    text = str(value).strip()
    suffix = "%" if text.endswith("%") else ""
    cleaned = text[:-1] if suffix else text
    cleaned = cleaned.replace(",", "").replace(" ", "")
    try:
        number = float(cleaned)
    except ValueError:
        return None, "", 0
    decimals = len(cleaned.split(".")[1]) if "." in cleaned else 0
    return number, suffix, decimals


def count_up(value: object, suffix: str = "") -> None:
    """Count from 0 to ``value`` in 1.2s when the frame is on screen.

    Uses Streamlit's HTML component. Reduced motion shows the final value.
    """
    number, parsed_suffix, decimals = _count_target(value)
    if number is None:
        st.markdown(html.escape(str(value)))
        return
    shown_suffix = suffix or parsed_suffix
    components.html(
        f"""
        <div id="n" style="font-family:Georgia,serif;font-size:2.4rem;color:#10263D;line-height:1.1">0</div>
        <script>
        (function () {{
          const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          const node = document.getElementById("n");
          const target = {number};
          const suffix = {json.dumps(shown_suffix)};
          const decimals = {decimals};
          const format = function (v) {{
            const body = decimals ? v.toFixed(decimals) : Math.round(v).toLocaleString("en-GB");
            return body + suffix;
          }};
          const paint = function (v) {{ node.textContent = format(v); }};
          if (reduce) {{ paint(target); return; }}
          const ease = function (t) {{ return 1 - Math.pow(1 - t, 3); }};
          const start = performance.now();
          const step = function (now) {{
            const t = Math.min(1, (now - start) / 1200);
            paint(target * ease(t));
            if (t < 1) requestAnimationFrame(step);
          }};
          const observer = new IntersectionObserver(function (entries) {{
            if (entries.some(function (entry) {{ return entry.isIntersecting; }})) {{
              observer.disconnect();
              requestAnimationFrame(step);
            }}
          }});
          observer.observe(node);
        }})();
        </script>
        """,
        height=56,
    )


def hero(
    eyebrow: str,
    title: str,
    subtitle: str,
    big_number: object | None = None,
    big_label: str | None = None,
    links: list[tuple[str, str]] | None = None,
) -> None:
    """Gradient header with an optional count-up ring and text links."""
    number, suffix, decimals = _count_target(big_number) if big_number is not None else (None, "", 0)
    if number is None:
        ring = ""
    else:
        ring = f"""
        <div class="kpi-ring" aria-label="{html.escape(big_label or 'Key figure')}">
          <b class="countup" data-target="{number}" data-suffix="{html.escape(suffix)}" data-decimals="{decimals}">0</b>
          <span>{html.escape(big_label or "")}</span>
        </div>
        """
    link_html = ""
    if links:
        anchors = "".join(
            f'<a class="hero-cta{" primary" if index == 0 else ""}" href="{html.escape(href)}">{html.escape(label)}</a>'
            for index, (href, label) in enumerate(links)
        )
        link_html = f'<div class="hero-ctas">{anchors}</div>'
    st.html(
        f"""
        <section class="hero">
          <div class="hero-grid">
            <div>
              <div class="eyebrow">{html.escape(eyebrow)}</div>
              <h1>{html.escape(title)}</h1>
              <p>{html.escape(subtitle)}</p>
              {link_html}
            </div>
            {ring}
          </div>
        </section>
        <script>
        (function () {{
          const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          const ease = function (t) {{ return 1 - Math.pow(1 - t, 3); }};
          document.querySelectorAll(".countup").forEach(function (node) {{
            if (node.dataset.bound) return;
            node.dataset.bound = "1";
            const target = parseFloat(node.dataset.target);
            const suffix = node.dataset.suffix || "";
            const decimals = parseInt(node.dataset.decimals || "0", 10);
            const format = function (v) {{
              const body = decimals ? v.toFixed(decimals) : Math.round(v).toLocaleString("en-GB");
              return body + suffix;
            }};
            if (!isFinite(target) || reduce) {{ node.textContent = format(target || 0); return; }}
            const start = function () {{
              const t0 = performance.now();
              const step = function (now) {{
                const t = Math.min(1, (now - t0) / 1200);
                node.textContent = format(target * ease(t));
                if (t < 1) requestAnimationFrame(step);
              }};
              requestAnimationFrame(step);
            }};
            const observer = new IntersectionObserver(function (entries) {{
              if (entries.some(function (entry) {{ return entry.isIntersecting; }})) {{
                observer.disconnect();
                start();
              }}
            }});
            observer.observe(node);
          }});
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def kpi_card(label: str, value: object, pct: float | None = None, accent: bool = False) -> None:
    """White card with a Fraunces figure and a thin bar. Amber marks double exclusion."""
    number, suffix, decimals = _count_target(value)
    width = 0.0
    if pct is not None:
        share = float(pct)
        if share > 1:
            share = share / 100.0
        width = max(0.0, min(100.0, share * 100.0))
    shown = html.escape(str(value)) if number is None else "0"
    figure = (
        f'<div class="kpi-num countup" data-target="{number}" data-suffix="{html.escape(suffix)}" '
        f'data-decimals="{decimals}">{shown}</div>'
        if number is not None
        else f'<div class="kpi-num">{shown}</div>'
    )
    bar = f'<div class="bar-track"><span class="bar-fill" style="--w:{width:.1f}%"></span></div>' if pct is not None else ""
    st.html(
        f"""
        <article class="kpi-card{' kpi-amber' if accent else ''}" style="--i:0">
          <div class="kpi-label">{html.escape(label)}</div>
          {figure}
          {bar}
        </article>
        <script>
        (function () {{
          const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          const ease = function (t) {{ return 1 - Math.pow(1 - t, 3); }};
          document.querySelectorAll(".countup").forEach(function (node) {{
            if (node.dataset.bound) return;
            node.dataset.bound = "1";
            const target = parseFloat(node.dataset.target);
            const suffix = node.dataset.suffix || "";
            const decimals = parseInt(node.dataset.decimals || "0", 10);
            const format = function (v) {{
              const body = decimals ? v.toFixed(decimals) : Math.round(v).toLocaleString("en-GB");
              return body + suffix;
            }};
            if (!isFinite(target) || reduce) {{ node.textContent = isFinite(target) ? format(target) : node.textContent; return; }}
            const t0 = performance.now();
            const step = function (now) {{
              const t = Math.min(1, (now - t0) / 1200);
              node.textContent = format(target * ease(t));
              if (t < 1) requestAnimationFrame(step);
            }};
            requestAnimationFrame(step);
          }});
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def ranked_bars(df: pd.DataFrame, label_col: str, value_col: str, *, accent: bool = False) -> None:
    """Ranked horizontal bars. Widths are shares of the largest value in the frame."""
    values = df[value_col].astype(float)
    peak = float(values.abs().max()) if len(values) else 1.0
    peak = peak if peak else 1.0
    as_share = bool(len(values) and float(values.max()) <= 1.5)
    as_percent = bool(len(values) and not as_share and float(values.max()) <= 100)
    rows: list[str] = []
    for index, row in enumerate(df.itertuples(index=False), start=1):
        label = html.escape(str(getattr(row, label_col)))
        value = float(getattr(row, value_col))
        if as_share:
            text = f"{value:.1%}"
        elif as_percent:
            text = f"{value:.1f}%"
        else:
            text = f"{value:,.0f}"
        width = max(0.0, min(100.0, abs(value) / peak * 100.0))
        fill = "bar-fill amber-fill" if accent or "neither" in label.lower() else "bar-fill"
        rows.append(
            f'<div class="rank-row" style="--i:{index - 1}">'
            f'<span class="rank-n">{index}</span>'
            f'<span class="rank-name">{label}</span>'
            f'<span class="bar-track"><span class="{fill}" style="--w:{width:.1f}%"></span></span>'
            f'<span class="rank-val">{text}</span></div>'
        )
    st.html(f'<div class="rank-list">{"".join(rows)}</div>', unsafe_allow_javascript=True)


def pathway_ribbon(cells: dict[str, float]) -> None:
    """One stacked bar of the four pathway states, each labelled in a legend."""
    palette = {
        "Account only": "#0A7C86",
        "Neither": "#C97A12",
        "VUP and account": "#12355B",
        "VUP only": "#8FB8D9",
    }
    order = [key for key in ("Account only", "Neither", "VUP and account", "VUP only") if key in cells]
    order += [key for key in cells if key not in order]
    segments: list[str] = []
    legend: list[str] = []
    for key in order:
        share = max(0.0, float(cells[key]))
        color = palette.get(key, "#12355B")
        ink = "#10263D" if color == "#8FB8D9" else "#FFFFFF"
        label = f"{share:.1%}" if share >= 0.08 else ""
        segments.append(
            f'<div class="ribbon-seg" style="width:{share * 100:.2f}%;background:{color};color:{ink}">{label}</div>'
        )
        legend.append(
            f'<li><span class="swatch" style="background:{color}"></span>{html.escape(key)} · {share:.1%}</li>'
        )
    st.html(
        f'<div class="ribbon" role="img" aria-label="Pathway shares">{"".join(segments)}</div>'
        f'<ul class="ribbon-legend">{"".join(legend)}</ul>',
        unsafe_allow_javascript=True,
    )


def caterpillar(df: pd.DataFrame):
    """Double-exclusion caterpillar. The series are the columns already on ``df``."""
    from .charts import caterpillar as draw

    national = None
    if "national_rate" in df.columns and len(df):
        national = float(df["national_rate"].iloc[0])
    return draw(
        df,
        "double_exclusion_among_poor",
        "double_exclusion_among_poor_ci_low",
        "double_exclusion_among_poor_ci_high",
        "double_exclusion_among_poor_sample_n",
        national,
        "Double exclusion among poor households",
    )


def skeleton_rows(n: int) -> str:
    """Shimmer placeholders. The caller replaces them when a result is ready."""
    bars = "".join('<div class="skeleton"></div>' for _ in range(max(1, n)))
    return f'<div aria-hidden="true">{bars}</div>'


def footer() -> None:
    """Shared source and decision-support note."""
    st.markdown(
        """
        <div class="source-footer">
          Source: NISR EICV7 district aggregates, fieldwork October 2023 – October 2024,
          and district boundaries. Illustrative decision-support tool — not for individual
          eligibility decisions. AI tools were used to help write code and documentation;
          every number shown is computed from the EICV7 district aggregates.
        </div>
        """,
        unsafe_allow_html=True,
    )


def banner(text: str) -> None:
    st.markdown(f'<div class="lab-banner">{html.escape(text)}</div>', unsafe_allow_html=True)


def _kpi_markup(cards: list[dict[str, Any]], columns: int, pulse: bool) -> str:
    card_html: list[str] = []
    for index, card in enumerate(cards):
        meter = card.get("meter")
        meter_html = ""
        if meter is not None:
            width = max(0.0, min(100.0, float(meter)))
            meter_html = (
                f'<div class="kpi-meter" style="--meter:{width:.1f}%"><span></span></div>'
            )
        note = html.escape(str(card.get("note") or ""))
        note_color = html.escape(str(card.get("note_color") or "#3E4C59"))
        card_html.append(
            f"""
            <article class="kpi-card{' pulse' if pulse else ''}{' accent' if card.get('accent') else ''}" data-countup="1"
              data-target="{float(card['value'])}" data-kind="{html.escape(str(card['kind']))}"
              data-decimals="{int(card.get('decimals', 1))}" style="animation-delay:{index * 60}ms">
              <div class="kpi-label">{html.escape(str(card['label']))}</div>
              <div class="kpi-num" aria-label="{html.escape(str(card['label']))}">0</div>
              <div class="kpi-note" style="color:{note_color}">{note}</div>
              {meter_html}
            </article>
            """
        )
    css_columns = f"cols-{min(max(columns, 1), 4)}"
    return f"""
    <div class="kpi-row {css_columns}">{''.join(card_html)}</div>
    <script>
    (function () {{
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const ease = function (t) {{ return 1 - Math.pow(1 - t, 3); }};
      function format(value, kind, decimals) {{
        if (kind === "percent") return value.toFixed(decimals) + "%";
        if (kind === "integer") return Math.round(value).toLocaleString("en-GB");
        return value.toLocaleString("en-GB", {{
          minimumFractionDigits: decimals, maximumFractionDigits: decimals
        }});
      }}
      function run(card) {{
        const target = parseFloat(card.dataset.target);
        const kind = card.dataset.kind;
        const decimals = parseInt(card.dataset.decimals || "1", 10);
        const node = card.querySelector(".kpi-num");
        if (!isFinite(target)) {{ node.textContent = "—"; return; }}
        if (reduce) {{ node.textContent = format(target, kind, decimals); return; }}
        const start = performance.now();
        function frame(now) {{
          const progress = Math.min(1, (now - start) / 1200);
          node.textContent = format(target * ease(progress), kind, decimals);
          if (progress < 1) requestAnimationFrame(frame);
        }}
        requestAnimationFrame(frame);
      }}
      const cards = document.querySelectorAll("[data-countup]");
      if (!("IntersectionObserver" in window)) {{ cards.forEach(run); return; }}
      const observer = new IntersectionObserver(function (entries) {{
        entries.forEach(function (entry) {{
          if (entry.isIntersecting) {{ run(entry.target); observer.unobserve(entry.target); }}
        }});
      }}, {{ threshold: 0.35 }});
      cards.forEach(function (card) {{ observer.observe(card); }});
    }})();
    </script>
    """


def kpi_strip(cards: list[dict[str, Any]], *, columns: int = 4, pulse: bool = False) -> None:
    """Count-up KPI cards. The script eases for 1.2s and respects reduced motion."""
    st.html(_kpi_markup(cards, columns, pulse), unsafe_allow_javascript=True)


def tab_open(tab: Any) -> bool:
    """True when a tab should render. A missing flag means render every tab."""
    flag = getattr(tab, "open", None)
    return True if flag is None else bool(flag)


def show_chart(fig: Any, caption: str, alt: str, *, key: str | None = None) -> Any:
    """Render a Plotly figure full width, with a one-line reading underneath."""
    kwargs: dict[str, Any] = {
        "width": "stretch",
        "theme": None,
        "config": PLOTLY_CONFIG,
        "alt": alt,
    }
    state = None
    if key:
        state = st.plotly_chart(fig, key=key, on_select="rerun", selection_mode="points", **kwargs)
    else:
        st.plotly_chart(fig, **kwargs)
    st.caption(caption)
    return state


def selected_point_label(state: Any) -> str | None:
    """District name from a Plotly point selection, when the chart stored one."""
    selection = getattr(state, "selection", None)
    points = getattr(selection, "points", None) if selection is not None else None
    if not points:
        return None
    point = points[0]
    if not isinstance(point, dict):
        return None
    custom = point.get("customdata")
    if isinstance(custom, (list, tuple)) and custom:
        return str(custom[0])
    hover = point.get("hovertext") or point.get("label")
    return str(hover) if hover else None


def reliability_badge(label: str) -> str:
    kind = {"Reliable": "ok", "Interpret with caution": "warn", "Unreliable": "bad"}.get(label, "info")
    return f'<span class="badge badge-{kind}">{html.escape(label)}</span>'


def profile_heading(district: str, province: str, reliability: str, cluster: str) -> None:
    st.markdown(
        f"""
        <div style="margin-bottom:8px">
          <div style="color:#087E8B;font-size:.76rem;letter-spacing:.08em;font-weight:700;text-transform:uppercase">
            {html.escape(province)}
          </div>
          <h2 style="margin:4px 0 8px 0">{html.escape(district)}</h2>
          {reliability_badge(reliability)}
          <span class="badge badge-info">{html.escape(cluster)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert_feed(alerts: list[dict[str, str]]) -> None:
    if not alerts:
        st.info("No alerts match the current filters.", title="Alert feed")
        return
    cards = []
    for alert in alerts:
        severity = alert["severity"]
        cards.append(
            f"""
            <article class="alert-card">
              <span class="badge chip-{html.escape(severity)}">{html.escape(severity.title())}</span>
              <strong>{html.escape(alert["district"])}</strong>
              <p style="margin:8px 0 0 0">{html.escape(alert["text"])}</p>
            </article>
            """
        )
    st.markdown("".join(cards), unsafe_allow_html=True)


def copy_panel(text: str) -> None:
    """Copy button with an in-page confirmation. The brief text stays selectable."""
    payload = json.dumps(text).replace("<", "\\u003c")
    st.html(
        f"""
        <div>
          <button type="button" id="lab-copy" style="min-height:44px;border-radius:12px;
            border:1px solid #087E8B;background:#087E8B;color:#FFFFFF;font-weight:700;
            padding:8px 16px;cursor:pointer">Copy text</button>
          <div id="lab-toast" role="status" style="display:none;margin-top:8px;background:#17365D;
            color:#FFFFFF;border-radius:12px;padding:8px 12px;max-width:240px">Brief copied</div>
        </div>
        <script type="application/json" id="lab-brief-json">{payload}</script>
        <script>
        (function () {{
          const button = document.getElementById("lab-copy");
          const toast = document.getElementById("lab-toast");
          const raw = document.getElementById("lab-brief-json").textContent;
          button.addEventListener("click", async function () {{
            const text = JSON.parse(raw);
            const mark = function () {{
              button.textContent = "Copied";
              toast.style.display = "block";
            }};
            try {{
              await navigator.clipboard.writeText(text);
              mark();
              return;
            }} catch (err) {{
              const area = document.createElement("textarea");
              area.value = text;
              area.setAttribute("readonly", "");
              area.style.position = "fixed";
              area.style.left = "-9999px";
              document.body.appendChild(area);
              area.select();
              let copied = false;
              try {{ copied = document.execCommand("copy"); }} catch (ignore) {{ copied = false; }}
              area.remove();
              if (copied) {{ mark(); }}
              else {{ button.textContent = "Clipboard blocked — select the brief"; }}
            }}
          }});
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def download_frame(label: str, frame: pd.DataFrame, file_name: str, *, key: str) -> None:
    payload = frame.to_csv(index=False).encode("utf-8")
    if st.download_button(label, data=payload, file_name=file_name, mime="text/csv", key=key, width="stretch", icon=":material/download:"):
        st.toast("Download started")


def download_text(label: str, text: str, file_name: str, mime: str, *, key: str) -> None:
    if st.download_button(
        label,
        data=text.encode("utf-8"),
        file_name=file_name,
        mime=mime,
        key=key,
        width="stretch",
        icon=":material/download:",
    ):
        st.toast("Download started")


def llm_available() -> bool:
    """True only when a lab language-model key is configured. Default is off."""
    try:
        return bool(str(st.secrets.get("LAB_LLM_API_KEY", "")).strip())
    except Exception:
        return False


def maybe_rewrite_brief(brief: str, enabled: bool) -> tuple[str, bool]:
    """Rewrite using only the numbers in the brief. Any failure keeps the template.

    The request body contains the aggregated figures extracted from the template,
    not the surrounding prose and not microdata. The checkbox defaults to off.
    """
    if not enabled:
        return brief, False
    try:
        key = str(st.secrets.get("LAB_LLM_API_KEY", "")).strip()
        base = str(st.secrets.get("LAB_LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        model = str(st.secrets.get("LAB_LLM_MODEL", "gpt-4o-mini"))
    except Exception:
        return brief, False
    if not key or not base.startswith("https://"):
        return brief, False
    numbers = re.findall(r"\d[\d,]*(?:\.\d+)?%?", brief)
    if not numbers:
        return brief, False
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Write a 120 to 180 word briefing on district double exclusion in Rwanda "
                    "using only the aggregated figures in the user message. Do not add facts, "
                    "names, or recommendations that are not implied by those figures."
                ),
            },
            {"role": "user", "content": "Aggregated figures only: " + ", ".join(numbers)},
        ],
    }
    try:
        import urllib.request

        request = urllib.request.Request(
            base + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
        rewritten = str(body["choices"][0]["message"]["content"]).strip()
    except Exception:
        return brief, False
    if not rewritten:
        return brief, False
    return "AI-generated, verify before use.\n\n" + rewritten, True
