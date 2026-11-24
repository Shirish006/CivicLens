"""backend_api.py - Live backend bridge for CivicLens.

Connects Gemini 3.8 Flash multimodal analysis, authoritative BBMP routing,
TF-IDF duplicate detection, explainable 0-100 impact scoring,
and SQLite persistence to the modern CivicLens frontend.
"""
from __future__ import annotations

from datetime import datetime
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from PIL import Image

import ai_analysis
import database
import duplicate
import routing
from constants import DEPARTMENTS, TICKET_COLUMNS

# Ensure database is initialized
database.init_db()

EXTRA_COLUMNS = ["Impact", "Summary", "Action", "Language", "People"]

# Local coordinate lookup table for common Bengaluru wards and landmarks
LOCALITY_COORDS = {
    "indiranagar": (12.9784, 77.6408),
    "koramangala": (12.9352, 77.6245),
    "whitefield": (12.9698, 77.7500),
    "jayanagar": (12.9308, 77.5838),
    "malleshwaram": (13.0031, 77.5643),
    "hebbal": (13.0358, 77.5970),
    "hsr": (12.9121, 77.6446),
    "btm": (12.9166, 77.6101),
    "marathahalli": (12.9591, 77.6974),
    "mg road": (12.9756, 77.6066),
    "outer ring road": (12.9345, 77.6912),
    "bellandur": (12.9279, 77.6741),
    "yelahanka": (13.1007, 77.5963),
    "rajajinagar": (12.9915, 77.5554),
    "basavanagudi": (12.9421, 77.5753),
    "sarjapur": (12.8600, 77.7860),
    "shivajinagar": (12.9857, 77.6057),
    "vijayanagar": (12.9719, 77.5306),
    "jalahalli": (13.0537, 77.5401),
    "kengeri": (12.9081, 77.4842),
    "yeshwanthpur": (13.0280, 77.5409),
    "domlur": (12.9609, 77.6387),
    "majestic": (12.9767, 77.5713),
    "cox town": (12.9965, 77.6220),
    "kalyan nagar": (13.0221, 77.6403),
    "banashankari": (12.9255, 77.5468),
}


def _resolve_coordinates(location: str) -> tuple[float, float]:
    """Look up latitude and longitude for a given location or fallback to Bengaluru center."""
    loc_lower = (location or "").lower()
    for name, coords in LOCALITY_COORDS.items():
        if name in loc_lower:
            return coords
    return 12.9716, 77.5946


def _calculate_impact(
    severity: str,
    people: int,
    school: bool,
    hospital: bool,
    verified: bool = False,
) -> tuple[int, str, list[dict]]:
    """Explainable impact score out of 100 with exact breakdown schema for UI components."""
    clean_sev = severity.capitalize() if severity else "Medium"
    sev_pts = {"Low": 10, "Medium": 25, "High": 38, "Critical": 50}.get(clean_sev, 25)
    breakdown = [
        {
            "label": "Severity",
            "points": sev_pts,
            "max": 50,
            "source": "ai",
            "detail": f"Assessed as {clean_sev}",
        }
    ]

    if people <= 0:
        ppl_pts, ppl_detail, ppl_src = 0, "Not provided", "na"
    else:
        ppl_pts = 6 if people < 10 else 12 if people < 50 else 20 if people < 200 else 26 if people < 1000 else 30
        ppl_src = "verified" if verified else "user"
        ppl_detail = f"About {people:,} people"
    breakdown.append(
        {
            "label": "People affected",
            "points": ppl_pts,
            "max": 30,
            "source": ppl_src,
            "detail": ppl_detail,
        }
    )

    near = [n for n, f in (("school", school), ("hospital", hospital)) if f]
    if near:
        loc_pts = 20 if len(near) == 2 else 14
        loc_detail = "Near a " + " and a ".join(near)
        loc_src = "verified" if verified else "user"
    else:
        loc_pts, loc_detail, loc_src = 0, "None reported", "na"
    breakdown.append(
        {
            "label": "Sensitive locations",
            "points": loc_pts,
            "max": 20,
            "source": loc_src,
            "detail": loc_detail,
        }
    )

    score = min(100, max(0, sev_pts + ppl_pts + loc_pts))
    band = "Very high" if score >= 70 else "High" if score >= 50 else "Moderate" if score >= 30 else "Low"
    return score, band, breakdown


def submit_complaint(
    text: str,
    language: str,
    location: str,
    image_bytes: Optional[bytes] = None,
    people_affected: int = 0,
    near_school: bool = False,
    near_hospital: bool = False,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict:
    """Submit complaint through full pipeline: Gemini AI -> BBMP Routing -> TF-IDF Duplicates -> Impact -> SQLite."""
    # 1. Process uploaded photo if present
    pil_img = None
    image_path = None
    if image_bytes:
        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            os.makedirs("uploads", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_path = f"uploads/img_{ts}.png"
            pil_img.save(saved_path)
            image_path = saved_path
        except Exception:
            pil_img = None

    # 2. AI Multimodal Triage (Gemini 3.8 Flash + keyword fallback)
    analysis = ai_analysis.analyze_complaint(
        description=text,
        location=location,
        image_path=image_path,
    )

    category = analysis.get("category", "Roads")
    severity = analysis.get("severity", "Medium")
    severity_reason = analysis.get("severity_reason", "Routine civic issue requiring municipal attention.")
    summary = analysis.get("summary", text[:100])
    suggested_action = analysis.get("suggested_action", "Dispatch inspection crew.")
    detected_lang = analysis.get("detected_language", language)
    english_trans = analysis.get("english_translation", text)

    # 3. Authoritative BBMP Routing
    department = routing.get_official_department(category)

    # 4. Explainable Impact Score
    people = max(0, int(people_affected or 0))
    impact_score, impact_band, impact_breakdown = _calculate_impact(
        severity=severity,
        people=people,
        school=bool(near_school),
        hospital=bool(near_hospital),
        verified=False,
    )

    # 5. Geolocation Resolution
    if latitude is not None and longitude is not None:
        lat, lng = float(latitude), float(longitude)
    else:
        lat, lng = _resolve_coordinates(location)

    # 6. TF-IDF Cosine Similarity Duplicate Detection
    existing_df = database.get_all_complaints()
    raw_dups = duplicate.check_duplicates(
        new_text=english_trans,
        new_category=category,
        new_location=location,
        existing_df=existing_df,
        threshold=0.28,
    )
    formatted_dups = [
        {
            "id": d["id"],
            "similarity": round(float(d.get("similarity_pct", 50)) / 100.0, 2),
            "location": d.get("location", ""),
            "description": d.get("summary") or d.get("description", ""),
        }
        for d in raw_dups[:3]
    ]

    # 7. Store in SQLite Database
    complaint_id = database.generate_complaint_id()
    now = datetime.now().replace(second=0, microsecond=0)
    db_record = {
        "id": complaint_id,
        "description": text.strip(),
        "english_translation": english_trans,
        "language": detected_lang,
        "category": category,
        "severity": severity,
        "severity_reason": severity_reason,
        "summary": summary,
        "department": department,
        "suggested_action": suggested_action,
        "location": location.strip(),
        "latitude": lat,
        "longitude": lng,
        "image_path": image_path,
        "people_affected": people,
        "near_school": 1 if near_school else 0,
        "near_hospital": 1 if near_hospital else 0,
        "inputs_verified": 0,
        "impact_score": impact_score,
        "impact_breakdown": json.dumps(impact_breakdown),
        "duplicate_of": formatted_dups[0]["id"] if formatted_dups else "",
        "analysis_source": "gemini" if not analysis.get("_fallback") else "offline_rule",
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Pending",
    }
    database.insert_complaint(db_record)

    return {
        "complaint_id": complaint_id,
        "description": text.strip(),
        "location": location.strip(),
        "category": category,
        "severity": severity,
        "severity_reason": severity_reason,
        "summary": summary,
        "department": department,
        "suggested_action": suggested_action,
        "language_detected": detected_lang,
        "impact_score": impact_score,
        "impact_band": impact_band,
        "impact_breakdown": impact_breakdown,
        "duplicates": formatted_dups,
        "status": "Pending",
        "created_at": now,
        "image_bytes": image_bytes,
        "latitude": lat,
        "longitude": lng,
        "fallback_reason": analysis.get("fallback_note") if analysis.get("analysis_source") == "fallback" else None,
    }


def get_tickets() -> pd.DataFrame:
    """Retrieve all tickets from SQLite formatted to match the frontend contract."""
    df = database.get_all_complaints()
    if df.empty:
        return pd.DataFrame(columns=TICKET_COLUMNS + EXTRA_COLUMNS)

    out = pd.DataFrame()
    out["Complaint ID"] = df["id"].astype(str)
    out["Description"] = df["description"].fillna("").astype(str)
    out["Category"] = df["category"].fillna("Roads").astype(str)
    out["Severity"] = df["severity"].fillna("Medium").astype(str)
    out["Reason"] = df["severity_reason"].fillna("").astype(str)
    out["Department"] = df["department"].fillna("General Administration").astype(str)
    out["Location"] = df["location"].fillna("").astype(str)
    out["Date"] = pd.to_datetime(df["created_at"], errors="coerce")
    out["Status"] = df["status"].fillna("Pending").astype(str)

    # Optional / Extra Columns for UI details
    out["Impact"] = pd.to_numeric(df["impact_score"], errors="coerce").fillna(0).astype(int)
    out["Summary"] = df["summary"].fillna("").astype(str)
    out["Action"] = df["suggested_action"].fillna("").astype(str)
    out["Language"] = df["language"].fillna("English").astype(str)
    out["People"] = pd.to_numeric(df["people_affected"], errors="coerce").fillna(0).astype(int)
    out["Duplicate Of"] = df["duplicate_of"].fillna("").astype(str) if "duplicate_of" in df.columns else ""
    if "latitude" in df.columns:
        out["Latitude"] = pd.to_numeric(df["latitude"], errors="coerce").fillna(12.9716)
    if "longitude" in df.columns:
        out["Longitude"] = pd.to_numeric(df["longitude"], errors="coerce").fillna(77.5946)

    return out


def set_status(complaint_id: str, new_status: str) -> None:
    """Update ticket status directly in SQLite database."""
    database.update_status(complaint_id, new_status)
