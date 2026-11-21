"""complaint.py - Citizen Portal UI and submission handling for CivicLens.
Allows citizens to submit complaints in English, Kannada, or Hindi with optional photos.
Connects with Gemini AI for instant triage, translation, deterministic department routing,
duplicate detection (TF-IDF + Cosine Similarity), explainable impact scoring,
and persistent SQLite storage.
"""
from datetime import datetime
import json
import os
import uuid
import streamlit as st
from ai_analysis import analyze_complaint
from database import generate_complaint_id, get_all_complaints, insert_complaint
from duplicate import check_duplicates
from impact_score import calculate_impact_score, get_band_color
from routing import get_official_department


def save_uploaded_image(uploaded_file, complaint_id: str) -> str:
    """Save an uploaded image safely to the uploads/ directory and return its path."""
    os.makedirs("uploads", exist_ok=True)
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        ext = ".jpg"
    safe_name = f"{complaint_id}_{uuid.uuid4().hex[:6]}{ext}"
    target_path = os.path.join("uploads", safe_name)

    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return target_path


def render_severity_badge(severity: str) -> str:
    """Return styled HTML badge for severity level."""
    badge_class = {
        "Critical": "badge-critical",
        "High": "badge-high",
        "Medium": "badge-medium",
        "Low": "badge-low",
    }.get(severity, "badge-medium")
    return f'<span class="{badge_class}">{severity.upper()}</span>'


def render_complaint_form():
    """Render the Citizen Complaint Submission Portal."""
    st.subheader("📢 Report a Civic Issue")
    st.caption("Submit your grievance directly to municipal authorities. Multilingual input supported.")

    with st.form("complaint_form", clear_on_submit=False):
        col_lang, col_loc = st.columns([1, 2])
        with col_lang:
            language = st.selectbox(
                "Preferred Language / ಭಾಷೆ / भाषा",
                options=["English", "ಕನ್ನಡ (Kannada)", "हिन्दी (Hindi)"],
                index=0,
                help="You can write your complaint in any of these languages.",
            )
        with col_loc:
            location = st.text_input(
                "Location / Landmark *",
                placeholder="e.g., 80ft Road, near Sony World Signal, Koramangala",
                help="Specify landmark, street, or area to help field teams locate the issue quickly.",
            )

        description = st.text_area(
            "Issue Description *",
            placeholder=(
                "Describe the issue in detail. For example:\n"
                "• English: Overflowing garbage bin attracting stray dogs on 4th Main.\n"
                "• Kannada: ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿ ಬಿದ್ದಿದ್ದು ವಾಹನ ಸವಾರರಿಗೆ ತೊಂದರೆಯಾಗಿದೆ.\n"
                "• Hindi: मुख्य सड़क पर पानी की पाइपलाइन फूट गई है और पानी बह रहा है।"
            ),
            height=130,
        )

        uploaded_image = st.file_uploader(
            "Attach a Photo (Optional)",
            type=["jpg", "jpeg", "png"],
            help="Uploading a photo enables AI visual verification and accurate severity assessment.",
        )

        st.markdown("##### 📍 Context & Community Impact (Optional)")
        col_aff, col_sch, col_hosp = st.columns([1.5, 1, 1])
        with col_aff:
            people_affected = st.number_input(
                "Estimated people affected",
                min_value=0,
                max_value=100000,
                value=0,
                step=10,
                help="Rough estimate of citizens impacted daily.",
            )
        with col_sch:
            st.write("")
            near_school = st.checkbox("Near a school / college", help="Check if adjacent to educational institutes.")
        with col_hosp:
            st.write("")
            near_hospital = st.checkbox("Near a hospital / clinic", help="Check if near healthcare facilities.")

        submitted = st.form_submit_button("🚀 Submit Complaint", use_container_width=True)

    if submitted:
        if not description.strip():
            st.error("⚠️ Please provide an issue description before submitting.")
            return

        if not location.strip():
            st.error("⚠️ Please specify the location or landmark.")
            return

        # 1. Generate sequential unique ID
        complaint_id = generate_complaint_id()

        saved_image_path = None
        if uploaded_image is not None:
            saved_image_path = save_uploaded_image(uploaded_image, complaint_id)

        # 2. Run AI Triage
        with st.spinner("🤖 AI is analyzing, translating, and triaging your complaint..."):
            ai_result = analyze_complaint(
                description=description.strip(),
                location=location.strip(),
                image_path=saved_image_path,
            )

        # 3. Rule-based department routing
        official_department = get_official_department(ai_result.get("category", "Roads"))

        # 4. Duplicate Check against existing database records
        existing_df = get_all_complaints()
        duplicate_matches = check_duplicates(
            new_text=ai_result.get("english_translation", description.strip()),
            new_category=ai_result.get("category", "Roads"),
            new_location=location.strip(),
            existing_df=existing_df,
            threshold=0.40,
        )
        duplicate_ids = [m["id"] for m in duplicate_matches]
        duplicate_of_str = ", ".join(duplicate_ids)

        # 5. Calculate Explainable Civic Impact Score
        score, score_breakdown, score_band = calculate_impact_score(
            severity=ai_result.get("severity", "Medium"),
            people_affected=people_affected,
            near_school=near_school,
            near_hospital=near_hospital,
            inputs_verified=False,
        )

        # 6. Save persistently into SQLite
        ticket_record = {
            "id": complaint_id,
            "description": description.strip(),
            "english_translation": ai_result.get("english_translation", description.strip()),
            "language": language,
            "category": ai_result.get("category", "Roads"),
            "severity": ai_result.get("severity", "Medium"),
            "severity_reason": ai_result.get("severity_reason", ""),
            "summary": ai_result.get("summary", ""),
            "department": official_department,
            "suggested_action": ai_result.get("suggested_action", ""),
            "location": location.strip(),
            "image_path": saved_image_path,
            "people_affected": people_affected,
            "near_school": 1 if near_school else 0,
            "near_hospital": 1 if near_hospital else 0,
            "inputs_verified": 0,
            "impact_score": score,
            "impact_breakdown": json.dumps(score_breakdown),
            "duplicate_of": duplicate_of_str,
            "analysis_source": ai_result.get("analysis_source", "gemini"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Pending",
        }

        insert_complaint(ticket_record)

        # 7. Store in session_state for rendering
        ticket_record["score_band"] = score_band
        ticket_record["duplicate_matches"] = duplicate_matches
        ticket_record["parsed_breakdown"] = score_breakdown
        st.session_state["latest_submission"] = ticket_record

    # Render confirmation & Triage results
    if "latest_submission" in st.session_state:
        sub = st.session_state["latest_submission"]

        st.success(f"✅ Complaint Registered in Municipal Database! Ticket ID: `{sub['id']}`")

        # Duplicate Warning Notice if similar tickets exist
        dup_matches = sub.get("duplicate_matches", [])
        if dup_matches:
            st.warning(
                f"⚠️ **Possible Duplicate Detected:** We found {len(dup_matches)} existing complaint(s) with high similarity. "
                "Your grievance has been logged and linked to increase priority without deleting previous reports."
            )
            for m in dup_matches[:2]:
                st.markdown(
                    f"- Ticket **`{m['id']}`** ({m['similarity_pct']}% match) at *{m['location']}* — Status: `{m['status']}`"
                )

        if sub.get("analysis_source") == "fallback":
            st.info("ℹ️ Note: Gemini momentarily unavailable — keyword fallback analysis applied.")

        # Triage Result Card
        st.markdown("### 🏛️ Automated Municipal Triage & Routing")
        card_col1, card_col2, card_col3 = st.columns([1.2, 1.2, 1])
        with card_col1:
            st.markdown(f"**Grievance Category:** `{sub['category']}`")
            st.markdown(f"**Assessed Severity:** {render_severity_badge(sub['severity'])}", unsafe_allow_html=True)
        with card_col2:
            st.markdown(f"**Official Department:** `{sub['department']}`")
            st.markdown(f"**Status:** `{sub['status']}`")
        with card_col3:
            band = sub.get("score_band", "Routine")
            band_color = get_band_color(band)
            st.markdown(
                f"**Civic Impact Score:** "
                f'<span style="background-color: {band_color}; color: white; padding: 4px 10px; border-radius: 12px; font-weight: 700;">'
                f"{sub.get('impact_score', 0)}/100 ({band.upper()})</span>",
                unsafe_allow_html=True,
            )

        st.markdown(f"**Severity Rationale:** *{sub['severity_reason']}*")
        st.markdown(f"**Summary:** {sub['summary']}")
        st.markdown(f"**Suggested Field Action:** `{sub['suggested_action']}`")

        if sub.get("language") != "English" and sub.get("english_translation"):
            st.info(f"🌐 **Standardized English Translation:** {sub['english_translation']}")

        # Impact Score Breakdown
        breakdown = sub.get("parsed_breakdown", [])
        if breakdown:
            with st.expander("📊 View Civic Impact Score Breakdown", expanded=True):
                st.caption("Transparent score factors distinguishing citizen-reported data from verified facts:")
                for item in breakdown:
                    st.markdown(
                        f"- **+{item['points']} pts** | **{item['factor']}**: *{item['detail']}* "
                        f"`[{item['status']}]`"
                    )

        # Full Submission Details
        with st.expander("📄 View Full Submission Metadata", expanded=False):
            st.write(f"**Original Citizen Text:** {sub['description']}")
            st.write(f"**Reported Location:** {sub['location']}")
            st.write(f"**Impact Context:** ~{sub['people_affected']} citizens | Near School: {bool(sub['near_school'])} | Near Hospital: {bool(sub['near_hospital'])}")
            if sub.get("duplicate_of"):
                st.write(f"**Duplicate References:** `{sub['duplicate_of']}`")
            if sub["image_path"]:
                st.image(sub["image_path"], caption="Attached Citizen Photo", width=300)
