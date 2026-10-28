"""Visual theme for the Rwanda double-exclusion dashboard.

Tokens match the Overview and Pathways artboards. This module does not
load data or change any estimate.
"""

from __future__ import annotations

PAGE = "#FFFFFF"
CARD = "#FFFFFF"
CARD_BORDER = "#E3E9EF"
INK = "#10263D"
MUTED = "#5B6B7B"
NAVY = "#12355B"
NAVY_DEEP = "#0F2A43"
TEAL = "#0A7C86"
TEAL_DEEP = "#075A63"
AMBER = "#C97A12"
AMBER_TINT = "#FFF6E6"
AMBER_BORDER = "#EBD3A3"
LIGHT_BLUE = "#8FB8D9"
CREAM = "#F6E7C8"
MAP_MID = "#D99136"

FONT = "Inter, system-ui, sans-serif"
DISPLAY = "Fraunces, Georgia, serif"

# Choropleth only. Cream to amber to navy, as specified for the map.
SEQUENTIAL = [[0.0, CREAM], [0.55, MAP_MID], [1.0, NAVY]]

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');

:root{
  --ink:#10263D; --muted:#5B6B7B; --line:#E3E9EF; --bg:#FFFFFF; --soft:#F6F8FA;
  --navy:#12355B; --teal:#0A7C86; --amber:#C97A12; --amber-tint:#FFF6E6; --amber-line:#EBD3A3;
}

/* page */
.stApp{ background:var(--bg); color:var(--ink); font-family:'Inter',system-ui,sans-serif; font-size:15px; }
.block-container{ padding-top:2.2rem; max-width:1280px; }
[data-testid="stHeader"]{ background:rgba(255,255,255,.92); }
[data-testid="stAppViewContainer"], .main{ background:var(--bg); }

/* headings: smaller, calmer */
h1{ font-family:'Fraunces',serif !important; font-weight:500 !important; font-size:2rem !important; line-height:1.15 !important; letter-spacing:-.01em; }
h2{ font-family:'Fraunces',serif !important; font-weight:500 !important; font-size:1.4rem !important; line-height:1.2 !important; }
h3{ font-family:'Fraunces',serif !important; font-weight:500 !important; font-size:1.1rem !important; }
p, label, li{ font-size:.95rem; }
.stCaption, [data-testid="stCaptionContainer"]{ font-size:.82rem; color:var(--muted); }

/* SIDEBAR: light, readable, scrollable */
[data-testid="stSidebar"]{ background:var(--soft); border-right:1px solid var(--line); }
[data-testid="stSidebar"] *{ color:var(--ink); }
[data-testid="stSidebarContent"]{ overflow-y:auto !important; height:100vh; padding-bottom:3rem; scrollbar-width:thin; scrollbar-color:#C5D0DA transparent; }
[data-testid="stSidebarContent"]::-webkit-scrollbar{ width:8px; }
[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb{ background:#C5D0DA; border-radius:8px; }
[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb:hover{ background:#A9B8C5; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{ font-size:1rem !important; }
.side-label{ font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); font-weight:600; margin:1rem 0 .2rem; }

/* sidebar navigation */
[data-testid="stSidebarNav"] a{ border-radius:10px; padding:8px 12px; font-size:.92rem; transition:background .2s, transform .2s; }
[data-testid="stSidebarNav"] a:hover{ background:#E9EEF3; transform:translateX(3px); }
[data-testid="stSidebarNav"] a[aria-current="page"]{ background:#fff; border:1px solid var(--line); font-weight:600; box-shadow:0 1px 2px rgba(16,38,61,.06); }

/* sidebar inputs: ALWAYS visible */
[data-testid="stSidebar"] [data-baseweb="select"] > div{ background:#fff !important; border:1px solid #D5DEE6 !important; border-radius:10px !important; color:var(--ink) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] *{ color:var(--ink) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] svg{ fill:var(--muted) !important; }
[data-testid="stSidebar"] [role="radiogroup"] label{ background:#fff; border:1px solid #D5DEE6; border-radius:10px; padding:6px 12px; transition:border-color .2s, background .2s; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover{ border-color:var(--teal); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){ background:#E8F3F4; border-color:var(--teal); }

/* BUTTONS (sidebar and main): dark text on white, clear border */
.stButton > button, .stDownloadButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stDownloadButton"] button{
  background:#fff !important; color:var(--ink) !important; border:1px solid #CBD6E0 !important; border-radius:10px !important;
  font-weight:500; padding:.55rem .9rem; transition:transform .15s, border-color .2s, box-shadow .2s; }
.stButton > button p, .stDownloadButton > button p, .stButton > button span, .stDownloadButton > button span,
.stButton > button div, .stDownloadButton > button div{ color:var(--ink) !important; }
.stButton > button svg, .stDownloadButton > button svg{ fill:var(--ink) !important; }
.stButton > button:hover, .stDownloadButton > button:hover{ border-color:var(--teal) !important; box-shadow:0 4px 12px rgba(10,124,134,.12); transform:translateY(-1px); }
.stButton > button:active, .stDownloadButton > button:active{ transform:scale(.97); }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible{ outline:2px solid var(--teal); outline-offset:2px; }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"]{ background:var(--navy) !important; border-color:var(--navy) !important; }
.stButton > button[kind="primary"] p, [data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span, [data-testid="stBaseButton-primary"] div{ color:#fff !important; }

/* cards */
[data-testid="stMetric"]{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:16px 18px; box-shadow:0 1px 2px rgba(16,38,61,.04); transition:transform .25s, box-shadow .25s; }
[data-testid="stMetric"]:hover{ transform:translateY(-3px); box-shadow:0 12px 26px rgba(16,38,61,.10); }
[data-testid="stMetricValue"]{ font-family:'Fraunces',serif; font-size:2rem !important; color:var(--ink); }
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] > div,
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] label{
  font-size:.82rem; color:var(--muted); font-weight:500;
  white-space:normal !important; overflow:visible !important; text-overflow:unset !important; height:auto !important;
}
[data-testid="stPlotlyChart"], [data-testid="stDataFrame"]{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:8px; }

/* hero: compact */
.hero{ background:linear-gradient(115deg,#0F2A43,#12355B 45%,#0A6C78 100%); background-size:200% 200%; animation:drift 16s ease-in-out infinite alternate;
  border-radius:18px; padding:28px 34px; color:#fff; margin-bottom:16px; }
.hero, .hero *{ color:#fff; }
.hero h1{ font-size:2.1rem !important; line-height:1.1 !important; margin:.3rem 0 .4rem; }
.hero p{ font-size:.98rem; color:#D5E4EE; margin:0; max-width:40rem; }
.hero .eyebrow{ font-size:.7rem; letter-spacing:.16em; text-transform:uppercase; color:#A9D8DD; font-weight:600; }
.hero a{ display:inline-block; margin:14px 10px 0 0; padding:9px 16px; border-radius:10px; border:1.5px solid rgba(255,255,255,.45); font-size:.88rem; font-weight:500; text-decoration:none; transition:background .2s, transform .15s; color:#fff; }
.hero a:hover{ background:rgba(255,255,255,.15); transform:translateY(-1px); }
.hero a.primary, .hero a.primary *{ background:#D99136; border-color:#D99136; color:#0F2A43 !important; font-weight:600; }
.hero-grid{ display:flex; justify-content:space-between; gap:24px; align-items:center; }
.hero-ctas{ display:flex; flex-wrap:wrap; gap:0; }
.kpi-ring{ width:170px; height:170px; border-radius:50%; border:1.5px solid rgba(255,255,255,.28); background:rgba(255,255,255,.08);
  display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; animation:pulse 2.4s ease-out 1s 2; flex:0 0 auto; }
.kpi-ring b, .kpi-ring .countup{ font-family:'Fraunces',serif; font-size:2.2rem; font-weight:500; line-height:1; color:#fff; }
.kpi-ring span{ font-size:.75rem; max-width:120px; line-height:1.3; margin-top:6px; color:#D5E4EE; }

/* custom cards and bars used by the lab components */
.kpi-row{ display:grid; gap:12px; margin:8px 0 16px; }
.kpi-row.cols-2{ grid-template-columns:repeat(2,minmax(0,1fr)); }
.kpi-row.cols-3{ grid-template-columns:repeat(3,minmax(0,1fr)); }
.kpi-row.cols-4{ grid-template-columns:repeat(4,minmax(0,1fr)); }
.kpi-card{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:16px 18px; box-shadow:0 1px 2px rgba(16,38,61,.04);
  transition:transform .25s, box-shadow .25s; animation:fadeUp .55s cubic-bezier(.2,.7,.2,1) both; animation-delay:calc(var(--i,0)*70ms); }
.kpi-card:hover{ transform:translateY(-3px); box-shadow:0 12px 26px rgba(16,38,61,.10); }
.kpi-label{ color:var(--muted); font-weight:500; font-size:.82rem; white-space:normal; }
.kpi-num, .kpi-card .countup{ font-family:'Fraunces',serif; font-size:2rem; color:var(--ink); font-weight:500; line-height:1.1; }
.kpi-note{ color:var(--muted); font-size:.82rem; min-height:1.2em; margin-top:4px; }
.kpi-amber{ background:var(--amber-tint) !important; border-color:var(--amber-line) !important; }
.bar-track{ height:6px; background:#E3E9EF; border-radius:99px; overflow:hidden; margin-top:12px; }
.kpi-amber .bar-track{ background:var(--amber-line); }
.bar-fill{ display:block; height:100%; width:var(--w,0%); background:var(--teal); transform-origin:left; animation:grow .9s cubic-bezier(.2,.7,.2,1) both; }
.kpi-amber .bar-fill, .amber-fill{ background:var(--amber); }
.kpi-meter{ height:6px; background:#E3E9EF; border-radius:99px; overflow:hidden; margin-top:12px; }
.kpi-meter > span{ display:block; height:100%; width:var(--meter,0%); background:var(--teal); transform-origin:left; animation:grow .9s cubic-bezier(.2,.7,.2,1) both; }
.kpi-card.accent{ background:var(--amber-tint); border-color:var(--amber-line); }
.kpi-card.accent .kpi-meter > span{ background:var(--amber); }
.rank-list{ display:flex; flex-direction:column; gap:10px; }
.rank-row{ display:grid; grid-template-columns:28px minmax(90px,1fr) minmax(80px,1.4fr) auto; gap:10px; align-items:center;
  animation:fadeUp .55s cubic-bezier(.2,.7,.2,1) both; animation-delay:calc(var(--i,0)*70ms); }
.rank-n{ color:var(--muted); font-variant-numeric:tabular-nums; font-size:.85rem; }
.rank-name{ color:var(--ink); font-weight:600; font-size:.92rem; }
.rank-val{ color:var(--ink); font-variant-numeric:tabular-nums; font-weight:600; font-size:.92rem; }
.rank-row .bar-track{ margin-top:0; }
.ribbon{ display:flex; width:100%; min-height:44px; border-radius:12px; overflow:hidden; border:1px solid var(--line); }
.ribbon-seg{ display:flex; align-items:center; justify-content:center; color:#fff; font-size:.75rem; font-weight:600; padding:6px; min-width:0; overflow:hidden; }
.ribbon-legend{ display:flex; flex-wrap:wrap; gap:10px 16px; margin:10px 0 0; padding:0; list-style:none; }
.ribbon-legend li{ color:var(--ink); font-size:.85rem; display:flex; align-items:center; gap:6px; }
.swatch{ width:12px; height:12px; border-radius:3px; display:inline-block; border:1px solid rgba(16,38,61,.15); }
.map-card, .panel{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:12px 14px; margin-bottom:12px; }
.lab-banner{ background:var(--amber-tint); border:1px solid var(--amber-line); border-radius:14px; padding:12px 14px; color:var(--ink); margin-bottom:12px; }
.source-footer{ border-top:1px solid var(--line); margin-top:2rem; padding-top:.8rem; color:var(--muted); font-size:.78rem; }
[data-testid="stVerticalBlockBorderWrapper"]{ background:#fff; border:1px solid var(--line); border-radius:16px; }

/* tabs as pills — this Streamlit version uses stTab, not only baseweb tabs */
[data-baseweb="tab-list"], [data-testid="stTabs"] [role="tablist"]{ gap:6px; border-bottom:none; flex-wrap:wrap; }
[data-baseweb="tab"], [data-testid="stTab"]{ border-radius:999px !important; padding:6px 14px !important; font-size:.88rem; min-height:40px; transition:background .2s; border:1px solid transparent; }
[data-baseweb="tab"]:hover, [data-testid="stTab"]:hover{ background:#EEF2F6; }
[data-baseweb="tab"][aria-selected="true"], [data-testid="stTab"][aria-selected="true"]{ background:var(--ink) !important; color:#fff !important; }
[data-baseweb="tab"][aria-selected="true"] p, [data-testid="stTab"][aria-selected="true"] *{ color:#fff !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"]{ display:none; }
[data-testid="stPills"] button{ border-radius:999px; border:1px solid #D5DEE6; background:#fff; color:var(--ink); }
[data-testid="stPills"] button[aria-pressed="true"]{ background:var(--ink); color:#fff; border-color:var(--ink); }

/* MOTION: staggered entrance for every block, thin load bar, hover polish */
@keyframes fadeUp{ from{opacity:0; transform:translateY(12px)} to{opacity:1; transform:none} }
@keyframes drift{ 0%{background-position:0% 50%} 100%{background-position:100% 50%} }
@keyframes pulse{ 0%{box-shadow:0 0 0 0 rgba(217,145,54,.45)} 100%{box-shadow:0 0 0 16px rgba(217,145,54,0)} }
@keyframes grow{ from{transform:scaleX(0)} to{transform:scaleX(1)} }
@keyframes shimmer{ 0%{background-position:-200px 0} 100%{background-position:200px 0} }
@keyframes loadbar{ from{transform:scaleX(0)} to{transform:scaleX(1)} }
.main .element-container{ animation:fadeUp .55s cubic-bezier(.2,.7,.2,1) both; }
.main .element-container:nth-child(1){animation-delay:.00s} .main .element-container:nth-child(2){animation-delay:.06s}
.main .element-container:nth-child(3){animation-delay:.12s} .main .element-container:nth-child(4){animation-delay:.18s}
.main .element-container:nth-child(5){animation-delay:.24s} .main .element-container:nth-child(6){animation-delay:.30s}
.main .element-container:nth-child(n+7){animation-delay:.36s}
.skeleton{ height:18px; margin:8px 0; background:linear-gradient(90deg,#EEF2F6,#F8FAFC,#EEF2F6); background-size:400px 100%; animation:shimmer 1.4s linear infinite; border-radius:8px; }
.stApp::before{ content:""; position:fixed; top:0; left:0; right:0; height:3px; z-index:9999; transform-origin:left;
  background:linear-gradient(90deg,#0A7C86,#D99136); animation:loadbar 1.1s cubic-bezier(.2,.7,.2,1) both; }

@media (prefers-reduced-motion: reduce){
  *, *::before { animation:none !important; transition:none !important; }
  .bar-fill, .kpi-meter > span{ width:var(--w, var(--meter, 100%)); transform:none !important; }
}
@media (max-width:760px){
  .hero{ padding:20px; }
  .hero h1{ font-size:1.6rem !important; }
  .kpi-ring{ width:130px; height:130px; }
  .kpi-ring b, .kpi-ring .countup{ font-size:1.7rem; }
  .hero-grid{ flex-direction:column; align-items:flex-start; }
  .kpi-row.cols-4, .kpi-row.cols-3, .kpi-row.cols-2{ grid-template-columns:1fr; }
  [data-testid="stHorizontalBlock"]{ flex-wrap:wrap; }
  .rank-row{ grid-template-columns:24px 1fr auto; }
  .rank-row .bar-track{ grid-column:1 / -1; }
  .block-container{ padding-left:.8rem; padding-right:.8rem; }
}
</style>
"""



def apply_theme() -> None:
    """Inject the artboard stylesheet. Call it after any older page CSS."""
    import streamlit as st

    st.markdown(_CSS, unsafe_allow_html=True)


def plotly_font() -> dict[str, str | int]:
    """Shared Plotly font. Data series are unchanged."""
    return {"family": FONT, "color": INK, "size": 12}
