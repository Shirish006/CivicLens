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

# Initialize authentication session state
if "officer_authenticated" not in st.session_state:
    st.session_state["officer_authenticated"] = False

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


def render_officer_login():
    """Render the official municipal officer authentication screen."""
    st.subheader("🔐 Municipal Officer Portal Login")
    st.caption("Restricted access for authorized city engineers, ward officers, and municipal dispatchers.")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("officer_login_form"):
            st.markdown(
                """
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 18px; border-radius: 8px; margin-bottom: 16px;">
                    <strong style="color: #0B2545;">🏛️ Municipal Corporation Operations Gateway</strong><br>
                    <span style="font-size: 13px; color: #64748B;">Please enter your official municipal credentials to access the command center.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            username = st.text_input("Officer Username / Badge ID", placeholder="e.g. officer")
            password = st.text_input("Security Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("🔐 Sign In to Command Center", use_container_width=True)

            if submitted:
                # Standard demo credentials for hackathon evaluation
                if username.strip().lower() == "officer" and password == "civiclens123":
                    st.session_state["officer_authenticated"] = True
                    st.session_state["officer_name"] = "Ward Officer (BBMP West)"
                    st.success("Authentication successful! Loading Operations Dashboard...")
                    st.rerun()
                else:
                    st.error("⚠️ Invalid credentials. Demo login: Username: officer | Password: civiclens123")

        st.info("💡 **Demo Credentials:** Username: `officer` | Password: `civiclens123`")


# Sidebar Navigation
with st.sidebar:
    st.markdown("### 🏛️ Navigation")
    view_mode = st.radio(
        "Select Portal:",
        options=["📢 Citizen Portal", "📋 Officer Dashboard"],
        index=0,
    )
    st.divider()

    # Officer session indicator in sidebar
    if st.session_state.get("officer_authenticated", False):
        st.markdown("##### 👤 Active Session")
        st.caption(f"Logged in: **{st.session_state.get('officer_name', 'Officer')}**")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state["officer_authenticated"] = False
            st.rerun()
        st.divider()

    # Demo data seeder shortcut in sidebar
    st.markdown("##### ⚡ Demo Control")
    if st.button("🌱 Load Demo Data (12 tickets)", use_container_width=True):
        count = database.seed_sample_complaints()
        st.success(f"Loaded {count} sample complaints!")
        st.rerun()

    st.caption("CivicLens Smart City Hub v1.0")

# Render View: Citizen Portal is public; Officer Dashboard is protected
if view_mode == "📢 Citizen Portal":
    complaint.render_complaint_form()
else:
    if st.session_state.get("officer_authenticated", False):
        dashboard.render_dashboard()
    else:
        render_officer_login()
