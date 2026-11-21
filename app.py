"""CivicLens – AI Triage for Citizen Complaints
Streamlit Entry Point
"""
import importlib
import streamlit as st
import database
import complaint
import dashboard

# Dynamically reload submodules so code updates apply immediately in running sessions
importlib.reload(database)
importlib.reload(complaint)
importlib.reload(dashboard)

# Initialize database schema on startup
database.init_db()

# Configure page settings
st.set_page_config(
    page_title="CivicLens – AI Triage for Citizen Complaints",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Civic Government UI Styling
CUSTOM_CSS = """
<style>
    /* Clean font and layout */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Branded header block */
    .civic-header {
        background: linear-gradient(135deg, #0B2545 0%, #134074 100%);
        color: white;
        padding: 18px 24px;
        border-radius: 10px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .civic-title {
        font-size: 26px;
        font-weight: 700;
        margin: 0;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .civic-tagline {
        font-size: 14px;
        color: #8DA9C4;
        margin-top: 4px;
    }
    .civic-badge {
        background-color: #13A89E;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Severity badges */
    .badge-critical {
        background-color: #EF4444;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 12px;
        display: inline-block;
    }
    .badge-high {
        background-color: #F97316;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 12px;
        display: inline-block;
    }
    .badge-medium {
        background-color: #F59E0B;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 12px;
        display: inline-block;
    }
    .badge-low {
        background-color: #10B981;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 12px;
        display: inline-block;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Top Branded Header
st.markdown(
    """
    <div class="civic-header">
        <div>
            <div class="civic-title">🏛️ CivicLens</div>
            <div class="civic-tagline">AI Triage for Citizen Complaints • Smart City Municipal Operations</div>
        </div>
        <div>
            <span class="civic-badge">Active Prototype</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar Navigation
with st.sidebar:
    st.markdown("### 🏛️ Navigation")
    view_mode = st.radio(
        "Select Portal:",
        options=["📢 Citizen Portal", "📋 Officer Dashboard"],
        index=0,
    )
    st.divider()

    # Demo data seeder shortcut in sidebar
    st.markdown("##### ⚡ Demo Control")
    if st.button("🌱 Load Demo Data (12 tickets)", use_container_width=True):
        count = database.seed_sample_complaints()
        st.success(f"Loaded {count} sample complaints!")
        st.rerun()

    st.caption("CivicLens Smart City Hub v1.0")

# Render View
if view_mode == "📢 Citizen Portal":
    complaint.render_complaint_form()
else:
    dashboard.render_dashboard()
