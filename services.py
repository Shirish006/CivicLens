"""Bridge between the UI and the backend.

The UI only ever calls the three functions below. If you create a file named
backend_api.py next to app.py that exposes the same three functions, CivicLens
switches to it automatically (live mode). If it is missing, or a call fails,
the demo backend (mock_backend.py) keeps the app running.

CONTRACT for backend_api.py
---------------------------
submit_complaint(text, language, location, image_bytes=None,
                 people_affected=0, near_school=False, near_hospital=False) -> dict
    Runs Gemini analysis, routing, duplicate check and impact score, saves the
    ticket to SQLite and returns:
        complaint_id, description, location, category, severity, severity_reason,
        summary, department, suggested_action, language_detected,
        impact_score (0-100), impact_band ("Low"|"Moderate"|"High"|"Very high"),
        impact_breakdown: list of {label, points, max, source, detail}
            where source is "ai" | "user" | "verified" | "na",
        duplicates: list of {id, similarity (0-1), location, description},
        status, created_at, image_bytes

get_tickets() -> pandas.DataFrame
    Columns: Complaint ID, Description, Category, Severity, Reason, Department,
    Location, Date, Status. Optional extras: Impact, Summary, Action.

set_status(complaint_id, new_status) -> None
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import mock_backend as demo

try:
    import backend_api as _live  # your real backend, optional
    LIVE = all(hasattr(_live, n) for n in ("submit_complaint", "get_tickets", "set_status"))
except Exception:  # missing file or import error
    _live, LIVE = None, False


def submit_complaint(**kwargs) -> dict:
    if LIVE:
        try:
            return _live.submit_complaint(**kwargs)
        except Exception as exc:  # keep the demo alive if the API fails
            result = demo.submit_complaint(**kwargs)
            result["fallback_reason"] = str(exc)
            return result
    return demo.submit_complaint(**kwargs)


def get_tickets() -> pd.DataFrame:
    if LIVE:
        try:
            return _live.get_tickets()
        except Exception as exc:
            st.session_state["_backend_error"] = str(exc)
    return demo.get_tickets()


def set_status(complaint_id: str, new_status: str) -> None:
    if LIVE:
        try:
            return _live.set_status(complaint_id, new_status)
        except Exception as exc:
            st.session_state["_backend_error"] = str(exc)
    demo.set_status(complaint_id, new_status)


def reset_demo_data() -> None:
    st.session_state.pop("_tickets", None)
    st.session_state.pop("cp_result", None)
