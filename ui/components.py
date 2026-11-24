"""Reusable HTML building blocks (badges, cards, table, impact ring)."""
from __future__ import annotations

import html as _html

import pandas as pd
import streamlit as st

from constants import DEPARTMENTS
from ui import theme as T


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def esc(value) -> str:
    """Escape user text for safe HTML. Also neutralises $ so it is never read as math."""
    text = " ".join(str(value).split())
    return _html.escape(text, quote=True).replace("$", "&#36;")


def md(markup: str) -> None:
    """Render an HTML snippet. Lines are joined so markdown never mistakes it for code."""
    st.markdown("".join(line.strip() for line in markup.strip().splitlines()), unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Page chrome
# --------------------------------------------------------------------------- #
def masthead(section: str, live: bool) -> None:
    mode = "Live backend" if live else "Demo data"
    md(f"""
    <div class="cl-mast">
      <div class="cl-brand"><div class="cl-lens"></div>
        <div><div class="cl-word">CivicLens</div><div class="cl-tag">AI triage for citizen complaints</div></div>
      </div>
      <div class="cl-mast-right"><span>{esc(section)}</span><span class="cl-mode"><i></i>{mode}</span></div>
    </div>""")


def page_header(title: str, subtitle: str) -> None:
    md(f'<div class="cl-ph"><h1>{esc(title)}</h1><div>{esc(subtitle)}</div></div>')


# --------------------------------------------------------------------------- #
# Badges
# --------------------------------------------------------------------------- #
def severity_badge(severity: str) -> str:
    color = T.SEVERITY.get(severity, T.MUTED)
    tint = T.SEVERITY_TINT.get(severity, "#EEF2F6")
    return f'<span class="cl-badge" style="color:{color};background:{tint}"><i></i>{esc(severity)}</span>'


def status_badge(status: str) -> str:
    color = T.STATUS.get(status, T.MUTED)
    tint = T.STATUS_TINT.get(status, "#EEF2F6")
    return f'<span class="cl-badge" style="color:{color};background:{tint}"><i></i>{esc(status)}</span>'


def category_chip(category: str) -> str:
    return f'<span class="cl-chip">{esc(category)}</span>'


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def kpi_card(label: str, value, sub: str, accent: str) -> str:
    return (f'<div class="cl-kpi" style="border-left-color:{accent}">'
            f'<div class="cl-kpi-label">{esc(label)}</div>'
            f'<div class="cl-kpi-val">{esc(value)}</div>'
            f'<div class="cl-kpi-sub">{esc(sub)}</div></div>')


def ticket_table(df: pd.DataFrame, limit: int = 500) -> str:
    """Priority-ordered ticket table with severity-coloured left edge."""
    show_impact = "Impact" in df.columns
    heads = ["Complaint ID", "Description", "Category", "Severity", "Reason",
             "Department", "Location", "Date", "Status"] + (["Impact"] if show_impact else [])
    head_html = "".join(f"<th>{h}</th>" for h in heads)

    rows = []
    for _, r in df.head(limit).iterrows():
        desc = str(r["Description"])
        short = desc if len(desc) <= 100 else desc[:97].rstrip() + "..."
        date = r["Date"].strftime("%d %b %Y") if pd.notna(r["Date"]) else ""
        edge = T.SEVERITY.get(r["Severity"], T.LINE)
        dup_val = str(r.get("Duplicate Of") or "").strip()
        dup_badge = f' <span title="Duplicate of {esc(dup_val)}" style="color:#C2410C;background:#FFEDD5;padding:1px 5px;border-radius:4px;font-size:10px;font-weight:600;">🔗 Dup</span>' if dup_val else ''
        cells = [
            f'<td class="first" style="border-left-color:{edge}">{esc(r["Complaint ID"])}{dup_badge}</td>',
            f'<td class="desc" title="{esc(desc)}">{esc(short)}</td>',
            f'<td>{category_chip(r["Category"])}</td>',
            f'<td>{severity_badge(r["Severity"])}</td>',
            f'<td class="reason">{esc(r["Reason"])}</td>',
            f'<td>{esc(r["Department"])}</td>',
            f'<td>{esc(r["Location"])}</td>',
            f'<td class="nowrap">{date}</td>',
            f'<td>{status_badge(r["Status"])}</td>',
        ]
        if show_impact:
            cells.append(f'<td class="num">{esc(r["Impact"])}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return (f'<div class="cl-tablewrap"><table class="cl-table"><thead><tr>{head_html}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def empty_state(title: str, hint: str) -> None:
    md(f'<div class="cl-empty"><b>{esc(title)}</b><br>{esc(hint)}</div>')


# --------------------------------------------------------------------------- #
# Citizen portal
# --------------------------------------------------------------------------- #
_SOURCE = {
    "ai": ("AI-assessed", "cl-src-ai"),
    "user": ("Citizen-reported, unverified", "cl-src-user"),
    "verified": ("Officer-verified", "cl-src-ver"),
    "na": ("Not provided", "cl-src-na"),
}


def impact_ring(score: int, band: str) -> str:
    color = T.BAND_COLOR.get(band, T.TEAL)
    return (f'<div class="cl-ringwrap"><div class="cl-ring" style="background:conic-gradient({color} {score}%,#E3EAF1 0)">'
            f'<div><b>{score}</b><span>out of 100</span></div></div>'
            f'<div><div class="cl-band" style="color:{color}">{esc(band)} priority</div>'
            f'<div class="cl-muted">Civic Impact Score</div></div></div>')


def impact_breakdown(items: list[dict]) -> str:
    out = []
    for it in items:
        label, css = _SOURCE.get(it.get("source", "na"), _SOURCE["na"])
        pct = 0 if not it["max"] else round(100 * it["points"] / it["max"])
        out.append(
            f'<div class="cl-bd"><div class="cl-bd-top"><span>{esc(it["label"])}</span>'
            f'<span>{it["points"]} / {it["max"]}</span></div>'
            f'<div class="cl-bar"><i style="width:{pct}%"></i></div>'
            f'<div class="cl-bd-src"><span class="cl-src {css}">{label}</span>{esc(it.get("detail", ""))}</div></div>')
    return "".join(out)


def duplicate_warning(dups: list[dict]) -> str:
    items = "".join(
        f'<li><b>{esc(d["id"])}</b> at {esc(d.get("location", ""))} ({round(d["similarity"] * 100)}% similar)</li>'
        for d in dups)
    return (f'<div class="cl-warn"><b>Similar complaints already exist</b><br>'
            f'Yours is still registered. An officer will review the match and link them if they are the same issue.'
            f'<ul>{items}</ul></div>')


def how_it_works() -> str:
    steps = [
        ("Describe the problem", "Write in your own words. Add a photo if you have one."),
        ("AI assesses urgency", "Your complaint is categorised and ranked from Low to Critical."),
        ("The right team is notified", "It goes to the responsible department with a suggested action."),
    ]
    body = "".join(f'<div class="cl-step"><div class="cl-stepn">{i}</div><div><b>{esc(t)}</b>'
                   f'<span>{esc(d)}</span></div></div>' for i, (t, d) in enumerate(steps, 1))
    return f'<div class="cl-card"><div class="cl-ct">What happens next</div>{body}</div>'


def routing_card() -> str:
    rows = "".join(f'<div class="cl-route"><span>{category_chip(c)}</span><span>{esc(d)}</span></div>'
                   for c, d in DEPARTMENTS.items())
    return f'<div class="cl-card"><div class="cl-ct">Who handles what</div>{rows}</div>'
