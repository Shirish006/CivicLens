"""dashboard.py - Municipal Officer Dashboard for CivicLens.
Provides executive metrics, Plotly visualizations, custom priority sorting
(Critical -> High -> Medium -> Low), multi-facet filtering, status updates,
and detailed ticket inspection with officer verification.
"""
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from database import (
    get_all_complaints,
    get_complaint_by_id,
    seed_sample_complaints,
    update_status,
    update_verification,
)
from impact_score import calculate_impact_score, get_band_color

# Severity color constants matching design guidelines
SEVERITY_COLOR_MAP = {
    "Critical": "#EF4444",  # Red
    "High": "#F97316",      # Orange
    "Medium": "#F59E0B",    # Amber/Yellow
    "Low": "#10B981",       # Green
}

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def render_badge(severity: str) -> str:
    """Render HTML pill badge for table and detail views."""
    color = SEVERITY_COLOR_MAP.get(severity, "#6B7280")
    return f'<span style="background-color: {color}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;">{str(severity).upper()}</span>'


def render_dashboard():
    """Render the Municipal Officer Operations Dashboard."""
    st.subheader("📋 Municipal Officer Triage & Operations Dashboard")
    st.caption("Real-time city grievance intake, automated dispatch oversight, and field resolution tracking.")

    # Refresh data directly from database
    df = get_all_complaints()

    # Empty State Handling or Seeder
    if df.empty:
        st.info("ℹ️ No citizen complaints recorded yet.")
        if st.button("🌱 Load Demo Data (12 Realistic Complaints)"):
            count = seed_sample_complaints()
            st.success(f"Loaded {count} sample complaints across all 6 departments!")
            st.rerun()
        return

    # Add custom sorting columns
    df["severity_rank"] = df["severity"].map(SEVERITY_ORDER).fillna(4)
    df["impact_score"] = pd.to_numeric(df["impact_score"], errors="coerce").fillna(0)

    # 1. Top Executive Metric Cards
    total_count = len(df)
    critical_count = len(df[df["severity"] == "Critical"])
    high_count = len(df[df["severity"] == "High"])
    pending_count = len(df[df["status"] == "Pending"])
    resolved_count = len(df[df["status"] == "Resolved"])

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="font-size: 13px; color: #64748B; font-weight: 600;">TOTAL TICKETS</div>
                <div style="font-size: 28px; font-weight: 700; color: #0B2545;">{total_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 4px solid #EF4444;">
                <div style="font-size: 13px; color: #EF4444; font-weight: 600;">CRITICAL ALERTS</div>
                <div style="font-size: 28px; font-weight: 700; color: #EF4444;">{critical_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 4px solid #F97316;">
                <div style="font-size: 13px; color: #F97316; font-weight: 600;">HIGH PRIORITY</div>
                <div style="font-size: 28px; font-weight: 700; color: #F97316;">{high_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 4px solid #F59E0B;">
                <div style="font-size: 13px; color: #F59E0B; font-weight: 600;">PENDING ACTION</div>
                <div style="font-size: 28px; font-weight: 700; color: #F59E0B;">{pending_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col5:
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 4px solid #10B981;">
                <div style="font-size: 13px; color: #10B981; font-weight: 600;">RESOLVED</div>
                <div style="font-size: 28px; font-weight: 700; color: #10B981;">{resolved_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # 2. Interactive Plotly Visualizations
    chart_col1, chart_col2, chart_col3 = st.columns(3)

    with chart_col1:
        cat_counts = df["category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Count"]
        fig_cat = px.pie(
            cat_counts,
            names="Category",
            values="Count",
            title="Complaints by Category",
            hole=0.45,
            color_discrete_sequence=["#0B2545", "#13A89E", "#134074", "#8DA9C4", "#EE6C4D", "#293241"],
        )
        fig_cat.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=260)
        st.plotly_chart(fig_cat, use_container_width=True)

    with chart_col2:
        sev_counts = df["severity"].value_counts().reindex(["Critical", "High", "Medium", "Low"]).fillna(0).reset_index()
        sev_counts.columns = ["Severity", "Count"]
        fig_sev = px.bar(
            sev_counts,
            x="Severity",
            y="Count",
            title="Severity Distribution",
            color="Severity",
            color_discrete_map=SEVERITY_COLOR_MAP,
        )
        fig_sev.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=260, showlegend=False)
        st.plotly_chart(fig_sev, use_container_width=True)

    with chart_col3:
        dept_counts = df["department"].value_counts().reset_index()
        dept_counts.columns = ["Department", "Count"]
        fig_dept = px.bar(
            dept_counts,
            y="Department",
            x="Count",
            orientation="h",
            title="Workload by Department",
            color_discrete_sequence=["#13A89E"],
        )
        fig_dept.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=260)
        st.plotly_chart(fig_dept, use_container_width=True)

    st.divider()

    # 3. Filters
    st.markdown("##### 🔎 Filter & Search Complaints")
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)

    with f_col1:
        categories = ["All"] + sorted(list(df["category"].dropna().unique()))
        selected_cat = st.selectbox("Category", categories, index=0)
    with f_col2:
        departments = ["All"] + sorted(list(df["department"].dropna().unique()))
        selected_dept = st.selectbox("Department", departments, index=0)
    with f_col3:
        severities = ["All", "Critical", "High", "Medium", "Low"]
        selected_sev = st.selectbox("Severity", severities, index=0)
    with f_col4:
        statuses = ["All", "Pending", "In Progress", "Resolved"]
        selected_status = st.selectbox("Status", statuses, index=0)

    # Apply filters
    filtered_df = df.copy()
    if selected_cat != "All":
        filtered_df = filtered_df[filtered_df["category"] == selected_cat]
    if selected_dept != "All":
        filtered_df = filtered_df[filtered_df["department"] == selected_dept]
    if selected_sev != "All":
        filtered_df = filtered_df[filtered_df["severity"] == selected_sev]
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    # Custom Sort: Critical -> High -> Medium -> Low, then impact_score DESC, then created_at DESC
    filtered_df = filtered_df.sort_values(
        by=["severity_rank", "impact_score", "created_at"],
        ascending=[True, False, False],
    )

    st.markdown(f"**Showing {len(filtered_df)} of {len(df)} complaints** (Sorted: Critical ➔ High ➔ Medium ➔ Low)")

    # 4. Complaints Table
    display_cols = [
        "id",
        "category",
        "severity",
        "department",
        "location",
        "impact_score",
        "duplicate_of",
        "status",
        "created_at",
    ]
    formatted_table = filtered_df[display_cols].copy()
    formatted_table["duplicate_of"] = formatted_table["duplicate_of"].apply(
        lambda x: "⚠️ Potential Duplicate" if str(x).strip() else "Unique"
    )

    st.dataframe(
        formatted_table.rename(
            columns={
                "id": "Ticket ID",
                "category": "Category",
                "severity": "Severity",
                "department": "Department",
                "location": "Location",
                "impact_score": "Score",
                "duplicate_of": "Duplicate Check",
                "status": "Status",
                "created_at": "Logged Date",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # 5. Ticket Detail & Status Management View
    st.markdown("### 🛠️ Officer Ticket Inspection & Action Panel")

    ticket_ids = filtered_df["id"].tolist()
    if not ticket_ids:
        st.info("No tickets match the current filters.")
        return

    selected_ticket_id = st.selectbox("Select Ticket ID to Inspect / Action:", options=ticket_ids)
    ticket = get_complaint_by_id(selected_ticket_id)

    if ticket:
        det_col1, det_col2 = st.columns([1.4, 1.1])

        with det_col1:
            st.markdown(f"#### Ticket: `{ticket['id']}`")
            st.markdown(
                f"**Category:** `{ticket['category']}` &nbsp;|&nbsp; "
                f"**Severity:** {render_badge(ticket['severity'])} &nbsp;|&nbsp; "
                f"**Department:** `{ticket['department']}`",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Location:** {ticket['location']}")
            st.markdown(f"**Severity Rationale:** *{ticket['severity_reason']}*")
            st.markdown(f"**Suggested Field Action:** `{ticket['suggested_action']}`")
            st.markdown(f"**Original Text ({ticket['language']}):**\n> {ticket['description']}")

            if ticket["language"] != "English" and ticket.get("english_translation"):
                st.info(f"🌐 **English Translation:** {ticket['english_translation']}")

            # Duplicate references if present
            if ticket.get("duplicate_of"):
                st.warning(f"⚠️ **Duplicate Linkage:** Matches prior complaint(s): `{ticket['duplicate_of']}`")

            # Impact Breakdown List
            st.markdown("##### 📊 Civic Impact Score Factors")
            try:
                breakdown = json.loads(ticket.get("impact_breakdown") or "[]")
            except Exception:
                breakdown = []

            if breakdown:
                for b in breakdown:
                    st.markdown(f"- **+{b['points']} pts** | **{b['factor']}**: {b['detail']} `[{b['status']}]`")
            else:
                st.caption("Baseline severity score applied.")

        with det_col2:
            st.markdown("#### Status & Officer Verification")

            # Status Update
            current_status = ticket.get("status", "Pending")
            status_index = ["Pending", "In Progress", "Resolved"].index(current_status) if current_status in ["Pending", "In Progress", "Resolved"] else 0
            new_status = st.selectbox("Workflow Status:", ["Pending", "In Progress", "Resolved"], index=status_index, key=f"status_{ticket['id']}")

            if st.button("💾 Save Status Update", use_container_width=True):
                success = update_status(ticket["id"], new_status)
                if success:
                    st.success(f"Status updated to '{new_status}' successfully!")
                    st.rerun()

            st.write("---")

            # Civic Impact Score Display
            score = ticket.get("impact_score", 0)
            is_verified = bool(ticket.get("inputs_verified", 0))
            band = "Urgent" if score >= 70 else ("Elevated" if score >= 40 else "Routine")
            band_color = get_band_color(band)

            st.markdown(
                f"**Current Impact Score:** "
                f'<span style="background-color: {band_color}; color: white; padding: 4px 10px; border-radius: 12px; font-weight: 700;">'
                f"{score}/100 ({band.upper()})</span>",
                unsafe_allow_html=True,
            )

            # Verification Controls
            st.markdown("##### 🛡️ Officer Field Verification")
            if is_verified:
                st.success("✅ Citizen inputs verified by municipal field inspector.")
                if st.button("↩️ Revert to Citizen-reported (Unverified)", use_container_width=True):
                    new_score, new_bd, _ = calculate_impact_score(
                        severity=ticket["severity"],
                        people_affected=ticket["people_affected"],
                        near_school=bool(ticket["near_school"]),
                        near_hospital=bool(ticket["near_hospital"]),
                        inputs_verified=False,
                    )
                    update_verification(ticket["id"], False, new_score, json.dumps(new_bd))
                    st.rerun()
            else:
                st.caption("Current status: `Citizen-reported, unverified`")
                if st.button("🛡️ Verify Citizen Inputs as Officer", use_container_width=True):
                    new_score, new_bd, _ = calculate_impact_score(
                        severity=ticket["severity"],
                        people_affected=ticket["people_affected"],
                        near_school=bool(ticket["near_school"]),
                        near_hospital=bool(ticket["near_hospital"]),
                        inputs_verified=True,
                    )
                    update_verification(ticket["id"], True, new_score, json.dumps(new_bd))
                    st.success("Marked inputs as verified!")
                    st.rerun()

            if ticket.get("image_path"):
                st.image(ticket["image_path"], caption="Attached Citizen Photo", use_container_width=True)
