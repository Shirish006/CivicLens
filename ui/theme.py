"""Design tokens and global CSS for CivicLens.

Navy carries authority, teal marks action, white and pale grey keep things clear.
Severity colours are used ONLY for severity so officers can read priority at a glance.
"""
import streamlit as st

NAVY = "#0B2545"
TEAL = "#13A89E"
TEAL_DEEP = "#0E8178"
INK = "#1B2A3B"
MUTED = "#5B6B7C"
LINE = "#DCE4EC"
PAGE = "#F2F5F8"

SEVERITY = {"Critical": "#C62828", "High": "#D9480F", "Medium": "#B7791F", "Low": "#2B7A4B"}
SEVERITY_TINT = {"Critical": "#FDECEC", "High": "#FEEFE5", "Medium": "#FFF4D6", "Low": "#E6F4EC"}
STATUS = {"Pending": "#566574", "In Progress": "#1A63D6", "Resolved": "#2B7A4B"}
STATUS_TINT = {"Pending": "#ECEFF2", "In Progress": "#E4EEFD", "Resolved": "#E6F4EC"}
BAND_COLOR = {"Very high": "#C62828", "High": "#D9480F", "Moderate": "#B7791F", "Low": "#2B7A4B"}

_FONTS = (
    "@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800"
    "&family=Noto+Sans+Devanagari:wght@400;600&family=Noto+Sans+Kannada:wght@400;600&display=swap');"
)

_ROOT = (
    f":root{{--navy:{NAVY};--teal:{TEAL};--teal-deep:{TEAL_DEEP};--ink:{INK};"
    f"--muted:{MUTED};--line:{LINE};--page:{PAGE};}}"
)

_CSS = """
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp li,
.stApp h1, .stApp h2, .stApp h3 {
  font-family:'Public Sans','Noto Sans Kannada','Noto Sans Devanagari',system-ui,-apple-system,'Segoe UI',sans-serif;
}
.stApp {background:var(--page); color:var(--ink);}
#MainMenu, footer, [data-testid="stToolbar"] {visibility:hidden;}
header[data-testid="stHeader"] {background:transparent;}
.block-container {padding-top:1.4rem; padding-bottom:3rem; max-width:1320px;}

/* Masthead */
.cl-mast {display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap;
  background:var(--navy); border-radius:12px; padding:.95rem 1.4rem; margin-bottom:1.5rem;
  border-bottom:3px solid var(--teal);}
.cl-brand {display:flex; align-items:center; gap:.85rem;}
.cl-lens {width:38px; height:38px; border-radius:50%; border:3px solid #fff; position:relative; flex:none;}
.cl-lens::before {content:""; position:absolute; inset:6px; border-radius:50%; border:2px solid var(--teal);}
.cl-lens::after {content:""; position:absolute; width:8px; height:8px; border-radius:50%; background:var(--teal);
  top:50%; left:50%; transform:translate(-50%,-50%);}
.cl-word {font-size:1.45rem; font-weight:800; letter-spacing:-.01em; color:#fff; line-height:1;}
.cl-tag {font-size:.82rem; color:#A9BCD3; margin-top:.25rem;}
.cl-mast-right {display:flex; align-items:center; gap:.9rem; color:#C9D8EA; font-size:.88rem;}
.cl-mode {border:1px solid rgba(255,255,255,.28); border-radius:999px; padding:.2rem .75rem; font-size:.78rem; color:#fff;}
.cl-mode i {display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--teal); margin-right:.45rem;}

/* Page header */
.cl-ph h1 {font-size:1.8rem; font-weight:800; color:var(--navy); margin:0 0 .3rem; padding:0; letter-spacing:-.015em;}
.cl-ph div {color:var(--muted); margin:0 0 1.2rem; font-size:1rem; max-width:64ch; line-height:1.5;}

/* Cards */
.cl-card {background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.15rem 1.3rem;
  box-shadow:0 1px 2px rgba(11,37,69,.05); margin-bottom:1rem;}
.cl-ct {font-weight:700; color:var(--navy); font-size:1.02rem; margin-bottom:.75rem;}
.cl-muted {color:var(--muted); font-size:.86rem;}
div[class*="st-key-card-"] {background:#fff; border:1px solid var(--line); border-radius:12px; padding:1rem 1.15rem;
  box-shadow:0 1px 2px rgba(11,37,69,.05);}
div[data-testid="stForm"] {background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.4rem 1.5rem;
  box-shadow:0 1px 2px rgba(11,37,69,.05);}

/* Inputs */
.stTextArea textarea, .stTextInput input, .stNumberInput input {border-radius:8px;}
[data-testid="stWidgetLabel"] p {font-weight:600; color:var(--navy); font-size:.9rem;}
.stButton button, .stDownloadButton button, div[data-testid="stFormSubmitButton"] button {border-radius:8px; font-weight:600;}
div[data-testid="stFormSubmitButton"] button {width:100%; padding:.65rem 1rem;}

/* Badges and chips */
.cl-badge {display:inline-flex; align-items:center; gap:.4rem; padding:.2rem .65rem; border-radius:999px;
  font-size:.78rem; font-weight:700; white-space:nowrap;}
.cl-badge i {width:8px; height:8px; border-radius:50%; background:currentColor;}
.cl-chip {display:inline-block; padding:.2rem .6rem; border-radius:6px; background:#E3F5F3; color:var(--teal-deep);
  font-weight:600; font-size:.78rem; white-space:nowrap;}
.cl-row {display:flex; align-items:center; gap:.6rem; flex-wrap:wrap;}

/* KPI cards */
.cl-kpi {background:#fff; border:1px solid var(--line); border-left:4px solid var(--navy); border-radius:10px;
  padding:.85rem 1rem; min-height:106px;}
.cl-kpi-label {font-size:.82rem; font-weight:600; color:var(--muted);}
.cl-kpi-val {font-size:2rem; font-weight:800; color:var(--navy); line-height:1.15; margin:.15rem 0;
  font-variant-numeric:tabular-nums;}
.cl-kpi-sub {font-size:.78rem; color:var(--muted);}

/* Citizen result */
.cl-receipt {display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:1rem; background:#fff;
  border:1px solid var(--line); border-left:5px solid var(--teal); border-radius:12px; padding:1.1rem 1.4rem; margin-bottom:1rem;}
.cl-id {font-size:1.9rem; font-weight:800; color:var(--navy); letter-spacing:.01em; font-variant-numeric:tabular-nums;}
.cl-warn {background:#FFF7E0; border:1px solid #F0D58A; border-radius:10px; padding:.9rem 1.1rem; margin-bottom:1rem; color:#5C4400;}
.cl-warn ul {margin:.4rem 0 0; padding-left:1.2rem;}
.cl-reason {font-size:1.02rem; color:var(--ink); line-height:1.5; margin:.8rem 0 0;}
.cl-dl {display:grid; grid-template-columns:140px 1fr; gap:.8rem 1rem; margin:1.1rem 0 0; padding-top:1rem; border-top:1px solid var(--line);}
.cl-dl dt {color:var(--muted); font-weight:600; font-size:.86rem;}
.cl-dl dd {margin:0; color:var(--ink); line-height:1.5;}

/* Impact score */
.cl-ringwrap {display:flex; align-items:center; gap:1.1rem; margin-bottom:1.1rem;}
.cl-ring {width:112px; height:112px; border-radius:50%; display:grid; place-items:center; flex:none;}
.cl-ring > div {width:86px; height:86px; border-radius:50%; background:#fff; display:flex; flex-direction:column;
  align-items:center; justify-content:center;}
.cl-ring b {font-size:1.9rem; color:var(--navy); line-height:1; font-variant-numeric:tabular-nums;}
.cl-ring span {font-size:.68rem; color:var(--muted); margin-top:.15rem;}
.cl-band {font-weight:800; font-size:1.15rem;}
.cl-bd {margin-bottom:.95rem;}
.cl-bd-top {display:flex; justify-content:space-between; font-weight:600; font-size:.88rem; color:var(--navy); margin-bottom:.3rem;}
.cl-bar {height:7px; background:#E3EAF1; border-radius:4px; overflow:hidden;}
.cl-bar i {display:block; height:100%; background:var(--teal); border-radius:4px;}
.cl-bd-src {margin-top:.35rem; font-size:.78rem; color:var(--muted); display:flex; gap:.5rem; align-items:center; flex-wrap:wrap;}
.cl-src {padding:.1rem .5rem; border-radius:5px; font-weight:600; font-size:.72rem;}
.cl-src-ai {background:#E3F5F3; color:var(--teal-deep);}
.cl-src-user {background:#FFF4D6; color:#7A5600;}
.cl-src-ver {background:#E6F4EC; color:#1E6B3F;}
.cl-src-na {background:#ECEFF2; color:#566574;}

/* How it works */
.cl-step {display:flex; gap:.85rem; margin-bottom:1rem;}
.cl-step:last-child {margin-bottom:0;}
.cl-stepn {flex:none; width:28px; height:28px; border-radius:50%; background:var(--navy); color:#fff; font-weight:700;
  font-size:.85rem; display:grid; place-items:center;}
.cl-step b {display:block; color:var(--navy); font-size:.95rem;}
.cl-step span {color:var(--muted); font-size:.88rem; line-height:1.45;}
.cl-route {display:flex; justify-content:space-between; align-items:center; gap:.8rem; padding:.5rem 0;
  border-bottom:1px solid #EDF1F5; font-size:.88rem;}
.cl-route:last-child {border-bottom:0;}
.cl-route span:last-child {color:var(--muted); text-align:right;}

/* Ticket table */
.cl-tablewrap {background:#fff; border:1px solid var(--line); border-radius:12px; overflow:auto; max-height:560px;}
.cl-table {width:100%; border-collapse:collapse; font-size:.86rem;}
.cl-table th {position:sticky; top:0; background:#EDF2F7; color:var(--navy); text-align:left; font-weight:700;
  padding:.7rem .85rem; border-bottom:1px solid var(--line); white-space:nowrap; z-index:1;}
.cl-table td {padding:.75rem .85rem; border-bottom:1px solid #EDF1F5; vertical-align:top; color:var(--ink); line-height:1.45;}
.cl-table td.first {border-left:4px solid transparent; font-weight:700; color:var(--navy); white-space:nowrap;}
.cl-table tr:hover td {background:#F7FAFC;}
.cl-table td.desc {min-width:260px; max-width:340px;}
.cl-table td.reason {min-width:230px; color:var(--muted);}
.cl-table td.nowrap {white-space:nowrap;}
.cl-table td.num {text-align:right; font-weight:700; font-variant-numeric:tabular-nums;}
.cl-empty {background:#fff; border:1px dashed var(--line); border-radius:12px; padding:2.2rem 1rem; text-align:center; color:var(--muted);}

/* Sidebar */
section[data-testid="stSidebar"] {background:var(--navy); border-right:0;}
section[data-testid="stSidebar"] * {color:#D3E0EF;}
section[data-testid="stSidebar"] div[role="radiogroup"] {gap:.25rem;}
section[data-testid="stSidebar"] div[role="radiogroup"] label {padding:.65rem .85rem; border-radius:8px; width:100%; cursor:pointer;}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {background:rgba(255,255,255,.07);}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {background:rgba(19,168,158,.24);}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) * {color:#fff; font-weight:700;}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {display:none;}
section[data-testid="stSidebar"] .stButton button {background:transparent; border:1px solid rgba(255,255,255,.3);}
.cl-side-note {font-size:.8rem; line-height:1.5; color:#9FB4CC;}

@media (max-width: 700px) {
  .cl-dl {grid-template-columns:1fr; gap:.2rem;}
  .cl-dl dd {margin-bottom:.7rem;}
  .cl-id {font-size:1.5rem;}
}
"""


def inject_css() -> None:
    css = "\n".join(line for line in (_FONTS + _ROOT + _CSS).splitlines() if line.strip())
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
