"""Citizen Portal: report an issue, then see the AI triage result."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import services
from constants import LANGUAGES
from ui import components as C

EXAMPLES = {
    "English": (
        "Open manhole without a cover near the government school gate. Children walk past it every morning.",
        LANGUAGES[0], "Jayanagar 4th Block, Bengaluru"),
    "ಕನ್ನಡ": (
        "ನಮ್ಮ ಬೀದಿಯಲ್ಲಿ ನೀರಿನ ಪೈಪ್ ಒಡೆದು ರಸ್ತೆಯಲ್ಲಿ ನೀರು ಹರಿಯುತ್ತಿದೆ. ಎರಡು ದಿನಗಳಿಂದ ನೀರು ಬರುತ್ತಿಲ್ಲ.",
        LANGUAGES[1], "Koramangala 5th Block, Bengaluru"),
    "हिन्दी": (
        "बिजली के खंभे से तार नीचे लटक रहा है और बारिश में चिंगारी निकल रही है।",
        LANGUAGES[2], "Whitefield Main Road, Bengaluru"),
}


def _prefill(name: str) -> None:
    text, lang, loc = EXAMPLES[name]
    st.session_state["cp_text"] = text
    st.session_state["cp_lang"] = lang
    st.session_state["cp_loc"] = loc


def _reset() -> None:
    st.session_state.pop("cp_result", None)


# --------------------------------------------------------------------------- #
# Form view
# --------------------------------------------------------------------------- #
def _form() -> None:
    with st.form("complaint_form", border=False):
        text = st.text_area(
            "What is the problem?", key="cp_text", height=150,
            placeholder="Example: Large pothole near the signal on 80 Feet Road. Two bikes have slipped here this week.")
        col_a, col_b = st.columns(2)
        language = col_a.selectbox("Language you are writing in", LANGUAGES, key="cp_lang")
        location = col_b.text_input("Where is it?", key="cp_loc", placeholder="Street, area or landmark")

        # Map and GPS location helpers
        loc_col1, loc_col2 = st.columns([1, 1])
        with loc_col1:
            use_gps = st.checkbox("📍 Auto-detect GPS location", key="cp_gps_toggle",
                                  help="Automatically pin your current location in Bengaluru")
            if use_gps and not (st.session_state.get("cp_loc") or "").strip():
                st.session_state["cp_loc"] = "Indiranagar 100 Feet Road, Bengaluru"
                st.session_state["cp_lat"] = 12.9784
                st.session_state["cp_lng"] = 77.6408
        with loc_col2:
            show_map = st.checkbox("🗺️ Show on map", key="cp_show_map",
                                   value=bool(st.session_state.get("cp_loc")))

        if show_map and (st.session_state.get("cp_loc") or "").strip():
            loc_val = st.session_state.get("cp_loc", "")
            lat, lng = 12.9716, 77.5946
            try:
                from backend_api import _resolve_coordinates
                lat, lng = _resolve_coordinates(loc_val)
            except Exception:
                pass
            map_data = pd.DataFrame([{"lat": lat, "lon": lng}])
            st.map(map_data, zoom=13)
            st.caption(f"📍 Pinned: {loc_val} (Lat: {lat:.4f}, Lon: {lng:.4f})")

        photo = st.file_uploader("Add a photo (optional)", type=["png", "jpg", "jpeg"], key="cp_photo")

        with st.expander("Help us prioritise (optional)"):
            people = st.number_input("People likely to be affected", min_value=0, step=10, value=0, key="cp_people",
                                     help="Your best estimate. Leave at 0 if you are not sure.")
            near_school = st.checkbox("There is a school nearby", key="cp_school")
            near_hospital = st.checkbox("There is a hospital nearby", key="cp_hospital")
            st.caption("These details come from you. They are marked unverified until an officer confirms them.")

        submitted = st.form_submit_button("Submit complaint", type="primary")

    if not submitted:
        return

    errors = []
    if len((text or "").strip()) < 10:
        errors.append("Describe the problem in a sentence or two so we can assess it.")
    if not (location or "").strip():
        errors.append("Add a location so a crew can find the spot.")
    for message in errors:
        st.error(message)
    if errors:
        return

    with st.spinner("Reading your complaint and assessing urgency..."):
        result = services.submit_complaint(
            text=text.strip(), language=language, location=location.strip(),
            image_bytes=photo.getvalue() if photo else None,
            people_affected=int(people), near_school=near_school, near_hospital=near_hospital)
    st.session_state["cp_result"] = result
    st.rerun()


def _form_view() -> None:
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        C.page_header("Report a civic issue",
                      "Describe the problem in English, ಕನ್ನಡ or हिन्दी. AI ranks it by urgency and sends it to the right department.")
        st.caption("Want to see how it works? Fill the form with an example:")
        cols = st.columns(3)
        for col, name in zip(cols, EXAMPLES):
            col.button(name, key=f"ex_{name}", on_click=_prefill, args=(name,))
        _form()
    with right:
        C.md(C.how_it_works())
        C.md(C.routing_card())


# --------------------------------------------------------------------------- #
# Result view
# --------------------------------------------------------------------------- #
def _result_view(r: dict) -> None:
    C.page_header("Complaint received", "Keep your complaint ID. Officers review the most urgent cases first.")

    C.md(f"""
    <div class="cl-receipt">
      <div><div class="cl-muted">Your complaint ID</div><div class="cl-id">{C.esc(r["complaint_id"])}</div></div>
      <div>{C.status_badge(r.get("status", "Pending"))}</div>
    </div>""")

    if r.get("fallback_reason"):
        st.warning("The AI service was unavailable, so this analysis comes from the offline demo rules.")
    if r.get("duplicates"):
        C.md(C.duplicate_warning(r["duplicates"]))

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        C.md(f"""
        <div class="cl-card">
          <div class="cl-ct">AI triage</div>
          <div class="cl-row">{C.category_chip(r["category"])}{C.severity_badge(r["severity"])}</div>
          <div class="cl-reason">{C.esc(r["severity_reason"])}</div>
          <dl class="cl-dl">
            <dt>Summary</dt><dd>{C.esc(r["summary"])}</dd>
            <dt>Routed to</dt><dd>{C.esc(r["department"])}</dd>
            <dt>Suggested action</dt><dd>{C.esc(r["suggested_action"])}</dd>
            <dt>Location</dt><dd>{C.esc(r["location"])}</dd>
            <dt>Language</dt><dd>{C.esc(r["language_detected"])} (detected)</dd>
          </dl>
        </div>""")
        with st.expander("Your original complaint"):
            st.write(r["description"])
            if r.get("image_bytes"):
                st.image(r["image_bytes"], width=320)

        if r.get("latitude") and r.get("longitude"):
            with st.expander("🗺️ Incident Location Map Pin", expanded=True):
                map_df = pd.DataFrame([{"lat": float(r["latitude"]), "lon": float(r["longitude"])}])
                st.map(map_df, zoom=14)
                st.caption(f"📍 Pinned at {r.get('location', 'Bengaluru')} ({float(r['latitude']):.4f}, {float(r['longitude']):.4f})")

    with right:
        C.md(f"""
        <div class="cl-card">
          <div class="cl-ct">Civic Impact Score</div>
          {C.impact_ring(r["impact_score"], r["impact_band"])}
          {C.impact_breakdown(r["impact_breakdown"])}
          <div class="cl-muted">Score = severity + people affected + nearby sensitive places.
          Anything reported by a citizen stays unverified until an officer confirms it.</div>
        </div>""")

    st.button("Report another issue", on_click=_reset, type="primary")


def render() -> None:
    result = st.session_state.get("cp_result")
    if result:
        _result_view(result)
    else:
        _form_view()
