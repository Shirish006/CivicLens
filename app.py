"""CivicLens: AI triage for citizen complaints.
Run with: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="CivicLens | AI triage for citizen complaints",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

import database  # noqa: E402
import services  # noqa: E402
from ui import components as C  # noqa: E402
from ui import theme as T  # noqa: E402
from ui.citizen_portal import render as citizen_portal  # noqa: E402
from ui.officer_dashboard import render as officer_dashboard  # noqa: E402
from ui.theme import inject_css  # noqa: E402

# Initialize database schema
database.init_db()

# Initialize session state for officer authentication
if "officer_authenticated" not in st.session_state:
    st.session_state["officer_authenticated"] = False

inject_css()


def render_officer_login() -> None:
    """Render the official municipal officer authentication screen matching modern theme."""
    C.page_header(
        "Municipal Officer Portal",
        "Restricted access for authorized BBMP engineers, ward officers, and municipal dispatchers.",
    )

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        with st.form("officer_login_form"):
            C.md(f"""
            <div class="cl-card" style="margin-bottom: 1.2rem; border-top: 4px solid {T.NAVY}">
              <div class="cl-ct">🔐 Municipal Operations Gateway</div>
              <div class="cl-muted">Please enter your municipal credentials to access the priority triage queue and live dispatch command center.</div>
            </div>
            """)
            username = st.text_input("Officer Username / Badge ID", placeholder="e.g. officer")
            password = st.text_input("Security Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In to Command Center", type="primary", use_container_width=True)

            if submitted:
                # Official demo credentials for evaluation
                if username.strip().lower() == "officer" and password == "civiclens123":
                    st.session_state["officer_authenticated"] = True
                    st.session_state["officer_name"] = "Ward Officer (BBMP West)"
                    st.success("Authentication successful! Loading Command Center...")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Demo Login: Username: officer | Password: civiclens123")

        st.info("💡 **Demo Credentials:** Username: `officer` | Password: `civiclens123`")


PAGES = {"Citizen Portal": citizen_portal, "Officer Dashboard": officer_dashboard}

with st.sidebar:
    st.write("")
    page = st.radio("Navigate", list(PAGES), key="nav", label_visibility="collapsed")
    st.write("")

    if services.LIVE:
        C.md(
            '<div class="cl-side-note"><b>🟢 Live Backend Connected</b><br>'
            'Integrated with Gemini 3.8 Flash multimodal analysis, BBMP routing, and SQLite storage.</div>'
        )
    else:
        C.md(
            '<div class="cl-side-note">Running on demo data: 24 sample tickets and offline triage rules. '
            'Add backend_api.py to connect Gemini and SQLite.</div>'
        )
        st.write("")
        st.button("Reset demo data", on_click=services.reset_demo_data)

    st.write("")

    # Officer authentication status in sidebar
    if st.session_state.get("officer_authenticated", False):
        st.markdown(f"**👤 Active Officer:** {st.session_state.get('officer_name', 'Municipal Officer')}")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state["officer_authenticated"] = False
            st.rerun()

    st.markdown("---")
    if st.button("🌱 Load Sample Data (12 tickets)", use_container_width=True):
        count = database.seed_sample_complaints()
        st.success(f"Loaded {count} sample complaints into SQLite database!")
        st.rerun()

# Top masthead
C.masthead(page, services.LIVE)

# Route to page with authentication check
if page == "Officer Dashboard":
    if st.session_state.get("officer_authenticated", False):
        officer_dashboard()
    else:
        render_officer_login()
else:
    citizen_portal()
