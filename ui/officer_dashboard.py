"""Officer Dashboard: KPIs, charts, filterable priority queue, status updates."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import services
from constants import CATEGORIES, DEPARTMENTS, SEVERITY_ORDER, STATUS_ORDER, TICKET_COLUMNS
from ui import components as C
from ui import theme as T

CHART_CFG = {"displayModeBar": False}


# --------------------------------------------------------------------------- #
# Data helpers
# --------------------------------------------------------------------------- #
def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col, default in (("Impact", 0), ("Summary", "-"), ("Action", "-")):
        if col not in df.columns:
            df[col] = default
    return df


def _sort_by_priority(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["_sev"] = d["Severity"].map({s: i for i, s in enumerate(SEVERITY_ORDER)}).fillna(99)
    d["_sta"] = d["Status"].map({s: i for i, s in enumerate(STATUS_ORDER)}).fillna(99)
    d = d.sort_values(["_sev", "_sta", "Impact", "Date"], ascending=[True, True, False, False])
    return d.drop(columns=["_sev", "_sta"])


def _apply_filters(df, cats, depts, sevs, stats, query) -> pd.DataFrame:
    if cats:
        df = df[df["Category"].isin(cats)]
    if depts:
        df = df[df["Department"].isin(depts)]
    if sevs:
        df = df[df["Severity"].isin(sevs)]
    if stats:
        df = df[df["Status"].isin(stats)]
    if query.strip() and not df.empty:
        haystack = df[["Complaint ID", "Description", "Location", "Reason"]].astype(str).agg(" ".join, axis=1)
        df = df[haystack.str.lower().str.contains(query.strip().lower(), regex=False)]
    return df


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def _kpis(df: pd.DataFrame) -> None:
    total = len(df)
    is_open = df["Status"] != "Resolved"
    crit = df["Severity"] == "Critical"
    high = df["Severity"] == "High"
    resolved = int((df["Status"] == "Resolved").sum())
    cards = [
        ("Total complaints", total, "All time", T.NAVY),
        ("Critical", int(crit.sum()), f"{int((crit & is_open).sum())} still open", T.SEVERITY["Critical"]),
        ("High priority", int(high.sum()), f"{int((high & is_open).sum())} still open", T.SEVERITY["High"]),
        ("Pending", int((df["Status"] == "Pending").sum()), "Waiting for action", T.STATUS["Pending"]),
        ("In progress", int((df["Status"] == "In Progress").sum()), "Crew assigned", T.STATUS["In Progress"]),
        ("Resolved", resolved, f"{round(100 * resolved / total) if total else 0}% of all", T.STATUS["Resolved"]),
    ]
    for col, (label, value, sub, accent) in zip(st.columns(6), cards):
        col.markdown(C.kpi_card(label, value, sub, accent), unsafe_allow_html=True)


def _style(fig: go.Figure, height: int = 290) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=6, b=0), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Public Sans, sans-serif", size=12, color=T.INK))
    return fig


def _charts(df: pd.DataFrame) -> None:
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1.container(key="card-cat"):
        C.md('<div class="cl-ct">Complaints by category</div>')
        counts = df["Category"].value_counts().reindex(CATEGORIES, fill_value=0)
        fig = go.Figure(go.Bar(x=counts.index, y=counts.values, marker_color=T.TEAL,
                               text=counts.values, textposition="outside", cliponaxis=False,
                               hovertemplate="%{x}: %{y}<extra></extra>"))
        fig.update_yaxes(showgrid=True, gridcolor="#EDF1F5", zeroline=False, visible=False)
        fig.update_xaxes(showgrid=False)
        st.plotly_chart(_style(fig), config=CHART_CFG, key="ch_cat")

    with c2.container(key="card-sev"):
        C.md('<div class="cl-ct">Complaints by severity</div>')
        counts = df["Severity"].value_counts().reindex(SEVERITY_ORDER, fill_value=0)
        fig = go.Figure(go.Pie(labels=counts.index, values=counts.values, hole=0.62, sort=False,
                               marker=dict(colors=[T.SEVERITY[s] for s in counts.index],
                                           line=dict(color="#fff", width=2)),
                               textinfo="value", hovertemplate="%{label}: %{value} (%{percent})<extra></extra>"))
        fig.add_annotation(text=f"<b>{len(df)}</b><br>complaints", x=0.5, y=0.5, showarrow=False,
                           font=dict(size=15, color=T.NAVY))
        _style(fig)
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.02, x=0.5, xanchor="center"))
        st.plotly_chart(fig, config=CHART_CFG, key="ch_sev")

    with c3.container(key="card-dept"):
        C.md('<div class="cl-ct">Complaints by department</div>')
        counts = df["Department"].value_counts().reindex(list(DEPARTMENTS.values()), fill_value=0).sort_values()
        fig = go.Figure(go.Bar(x=counts.values, y=counts.index, orientation="h", marker_color=T.NAVY,
                               text=counts.values, textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: %{x}<extra></extra>"))
        fig.update_xaxes(visible=False)
        fig.update_yaxes(automargin=True)
        st.plotly_chart(_style(fig), config=CHART_CFG, key="ch_dept")


def _filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.container(key="card-filters"):
        C.md('<div class="cl-ct">Filter the ticket queue</div>')
        f1, f2, f3, f4, f5 = st.columns([1, 1.3, 1, 1, 1.3])
        cats = f1.multiselect("Category", CATEGORIES, placeholder="All")
        depts = f2.multiselect("Department", list(DEPARTMENTS.values()), placeholder="All")
        sevs = f3.multiselect("Severity", SEVERITY_ORDER, placeholder="All")
        stats = f4.multiselect("Status", STATUS_ORDER, placeholder="All")
        query = f5.text_input("Search", placeholder="ID, place or keyword")
    return _apply_filters(df, cats, depts, sevs, stats, query)


def _queue(filtered: pd.DataFrame, total: int) -> None:
    left, right = st.columns([3, 1])
    with left:
        C.md(f'<div class="cl-ct" style="margin-top:1.2rem">Ticket queue</div>'
             f'<div class="cl-muted">Showing {len(filtered)} of {total} complaints, most urgent first.</div>')
    with right:
        cols = [c for c in TICKET_COLUMNS + ["Impact"] if c in filtered.columns]
        csv = filtered[cols].to_csv(index=False).encode("utf-8-sig")
        st.markdown('<div style="height:1.2rem"></div>', unsafe_allow_html=True)
        st.download_button("Download CSV", csv, file_name="civiclens_tickets.csv", mime="text/csv")

    if filtered.empty:
        C.empty_state("No complaints match these filters", "Clear a filter or search term to see more tickets.")
    else:
        st.markdown(C.ticket_table(filtered), unsafe_allow_html=True)
        if len(filtered) > 100:
            st.caption("Showing the 100 most urgent tickets. Narrow the filters or download the CSV for the rest.")


def _update_panel(filtered: pd.DataFrame) -> None:
    C.md('<div class="cl-ct" style="margin-top:1.4rem">Update a ticket</div>')
    if filtered.empty:
        st.caption("Select tickets with the filters above to update their status.")
        return

    labels = {r["Complaint ID"]: f'{r["Complaint ID"]} | {r["Severity"]} | {r["Location"]}'
              for _, r in filtered.iterrows()}
    left, right = st.columns([1, 1.2], gap="large")

    with left.container(key="card-update"):
        ticket_id = st.selectbox("Ticket", list(labels), format_func=labels.get)
        row = filtered[filtered["Complaint ID"] == ticket_id].iloc[0]
        current = row["Status"] if row["Status"] in STATUS_ORDER else STATUS_ORDER[0]
        new_status = st.radio("New status", STATUS_ORDER, index=STATUS_ORDER.index(current),
                              horizontal=True, key=f"status_{ticket_id}")
        if st.button("Update status", type="primary", disabled=new_status == current):
            services.set_status(ticket_id, new_status)
            st.toast(f"{ticket_id} marked {new_status}")
            st.rerun()

    with right:
        C.md(f"""
        <div class="cl-card">
          <div class="cl-row"><b style="color:{T.NAVY}">{C.esc(row["Complaint ID"])}</b>
            {C.severity_badge(row["Severity"])}{C.status_badge(row["Status"])}</div>
          <dl class="cl-dl">
            <dt>Summary</dt><dd>{C.esc(row["Summary"])}</dd>
            <dt>Suggested action</dt><dd>{C.esc(row["Action"])}</dd>
            <dt>Department</dt><dd>{C.esc(row["Department"])}</dd>
            <dt>Impact score</dt><dd>{C.esc(row["Impact"])} out of 100</dd>
          </dl>
        </div>""")


# --------------------------------------------------------------------------- #
def render() -> None:
    C.page_header("Officer dashboard", "Every citizen complaint in one queue, ranked by urgency.")
    df = _prepare(services.get_tickets())
    if df.empty:
        C.empty_state("No complaints yet", "New complaints from the Citizen Portal will appear here.")
        return

    _kpis(df)
    st.write("")
    _charts(df)
    st.write("")

    # Interactive Geographic Incident Map
    if "Latitude" in df.columns and "Longitude" in df.columns:
        valid_coords = df.dropna(subset=["Latitude", "Longitude"]).copy()
        if not valid_coords.empty:
            with st.expander("🗺️ City Incident Map (Geographic Distribution)", expanded=False):
                map_data = valid_coords.rename(columns={"Latitude": "lat", "Longitude": "lon"})
                st.map(map_data[["lat", "lon"]], zoom=11)
                st.caption(f"Visualizing {len(valid_coords)} geo-tagged incident locations across Bengaluru.")

    filtered = _sort_by_priority(_filters(df))
    _queue(filtered, len(df))
    _update_panel(filtered)
