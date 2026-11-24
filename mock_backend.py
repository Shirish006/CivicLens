"""Demo backend for CivicLens.

Lets the whole UI work with zero setup: keyword-based triage (English, Kannada,
Hindi), rule-based routing, an explainable impact score, simple duplicate
detection, and 24 seeded tickets. Data lives in st.session_state.

When your real modules (Gemini, SQLite, TF-IDF) are ready, expose them through
backend_api.py (see services.py). This file then becomes the offline fallback.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from constants import DEPARTMENTS, TICKET_COLUMNS

EXTRA_COLUMNS = ["Impact", "Summary", "Action", "Language", "People"]

ISSUE_LABEL = {
    "Roads": "Road damage",
    "Waste": "Uncollected or overflowing garbage",
    "Water": "Water leakage or supply problem",
    "Electricity": "Faulty street lighting or exposed electrical equipment",
    "Trees": "Fallen or unsafe tree",
    "Drainage": "Blocked or overflowing drain",
}

BASE_ACTION = {
    "Roads": "Send a road inspection crew, barricade the damaged area and schedule a patch repair.",
    "Waste": "Dispatch a collection vehicle, clear the waste and check the pickup schedule for this ward.",
    "Water": "Send a plumbing team to find the leak or supply fault and restore normal flow.",
    "Electricity": "Dispatch an electrical crew to make the area safe, then repair or replace the faulty equipment.",
    "Trees": "Send a tree-cutting team to remove the hazard and clear the debris.",
    "Drainage": "Dispatch a desilting crew to clear the blockage and inspect the nearby drain line.",
}

RESPONSE_TARGET = {
    "Critical": "within 4 hours",
    "High": "within 24 hours",
    "Medium": "within 3 days",
    "Low": "within 7 days",
}

# Order matters: on a tie the earlier category wins.
KEYWORDS = {
    "Roads": ["pothole", "road", "crack", "footpath", "pavement", "asphalt", "speed breaker",
              "गड्ढा", "सड़क", "रोड", "ಗುಂಡಿ", "ರಸ್ತೆ"],
    "Waste": ["garbage", "trash", "waste", "dustbin", "dump", "litter",
              "कचरा", "कूड़ा", "ಕಸ"],
    "Drainage": ["drain", "sewage", "sewer", "manhole", "gutter", "clogged", "waterlogging",
                 "नाला", "नाली", "सीवर", "मैनहोल", "ಚರಂಡಿ", "ಮ್ಯಾನ್‌ಹೋಲ್"],
    "Water": ["water", "pipe", "leak", "tap", "supply",
              "पानी", "पाइप", "लीक", "नल", "ನೀರು", "ಪೈಪ್", "ನಲ್ಲಿ"],
    "Electricity": ["streetlight", "street light", "light", "lamp", "electric", "wire", "transformer",
                    "pole", "spark", "power cut",
                    "बिजली", "तार", "खंभा", "ट्रांसफार्मर", "ವಿದ್ಯುತ್", "ತಂತಿ", "ಕಂಬ", "ದೀಪ"],
    "Trees": ["tree", "branch", "uprooted",
              "पेड़", "डाली", "ಮರ", "ಕೊಂಬೆ"],
}

CRITICAL_TERMS = [
    "live wire", "exposed wire", "hanging wire", "spark", "electrocut", "shock",
    "open manhole", "sinkhole", "collapse", "accident", "injur", "fell into", "fire", "gas leak",
    "चिंगारी", "करंट", "दुर्घटना", "खुला मैनहोल", "ಕಿಡಿ", "ಅಪಘಾತ", "ಶಾಕ್",
]

HIGH_SIGNALS = [
    "school", "hospital", "children", "kids", "elderly", "flood", "burst", "overflow",
    "sewage", "blocking", "blocked", "dangerous", "unsafe", "hazard", "days", "week", "no water",
    "स्कूल", "अस्पताल", "बच्चे", "खतरा", "खतरनाक", "ಶಾಲೆ", "ಆಸ್ಪತ್ರೆ", "ಮಕ್ಕಳು", "ಅಪಾಯ",
]

BASE_LEVEL = {"Roads": 1, "Waste": 0, "Drainage": 1, "Water": 1, "Electricity": 1, "Trees": 0}


# --------------------------------------------------------------------------- #
# Triage helpers
# --------------------------------------------------------------------------- #
def _hits(text: str, terms: list[str]) -> list[str]:
    t = text.lower()
    found = []
    for term in terms:
        if term.isascii():
            if re.search(r"\b" + re.escape(term), t):
                found.append(term)
        elif term in t:
            found.append(term)
    return found


def _detect_language(text: str) -> str:
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "Kannada"
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi"
    return "English"


def _classify(text: str) -> str:
    scores = {c: len(_hits(text, kws)) for c, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "Roads"


def _reason(sev: str, school: bool = False, hospital: bool = False) -> str:
    if sev == "Critical":
        return "Immediate risk to life or safety; needs a response within 4 hours."
    if sev == "High":
        place = " and ".join(p for p, flag in (("school", school), ("hospital", hospital)) if flag)
        base = (f"Reported near a {place} and likely to affect many people"
                if place else "Likely to worsen quickly or affect many residents")
        return base + "; needs action within 24 hours."
    if sev == "Medium":
        return "Causes daily disruption but no immediate danger; needs action within 3 days."
    return "Minor nuisance with no safety risk; can be scheduled within 7 days."


def _severity(text: str, category: str, people: int, school: bool, hospital: bool) -> tuple[str, str]:
    if _hits(text, CRITICAL_TERMS):
        return "Critical", _reason("Critical")
    level = BASE_LEVEL[category] + min(len(_hits(text, HIGH_SIGNALS)), 2)
    if school or hospital:
        level += 1
    if people >= 200:
        level += 1
    sev = ["Low", "Medium", "High"][min(level, 2)]
    return sev, _reason(sev, school, hospital)


def _action(category: str, sev: str) -> str:
    return f"{BASE_ACTION[category]} Target response: {RESPONSE_TARGET[sev]}."


def _impact(sev: str, people: int, school: bool, hospital: bool):
    """Explainable score out of 100: severity (50) + people affected (30) + sensitive places (20)."""
    sev_pts = {"Low": 10, "Medium": 25, "High": 38, "Critical": 50}[sev]
    breakdown = [{"label": "Severity", "points": sev_pts, "max": 50, "source": "ai",
                  "detail": f"Assessed as {sev}"}]

    if people <= 0:
        ppl_pts, ppl_detail, ppl_src = 0, "Not provided", "na"
    else:
        ppl_pts = 6 if people < 10 else 12 if people < 50 else 20 if people < 200 else 26 if people < 1000 else 30
        ppl_detail, ppl_src = f"About {people:,} people", "user"
    breakdown.append({"label": "People affected", "points": ppl_pts, "max": 30,
                      "source": ppl_src, "detail": ppl_detail})

    near = [n for n, f in (("school", school), ("hospital", hospital)) if f]
    if near:
        loc_pts, loc_detail, loc_src = (20 if len(near) == 2 else 14), "Near a " + " and a ".join(near), "user"
    else:
        loc_pts, loc_detail, loc_src = 0, "None reported", "na"
    breakdown.append({"label": "Sensitive locations", "points": loc_pts, "max": 20,
                      "source": loc_src, "detail": loc_detail})

    score = sev_pts + ppl_pts + loc_pts
    band = "Very high" if score >= 70 else "High" if score >= 50 else "Moderate" if score >= 30 else "Low"
    return score, band, breakdown


_GENERIC = {"bengaluru", "bangalore", "karnataka", "near", "the", "and", "for", "with"}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.lower()) if len(w) > 2 and w not in _GENERIC}


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _duplicates(description: str, location: str, category: str, existing: list[dict]) -> list[dict]:
    """Stand-in for TF-IDF + cosine similarity: token overlap on text and location."""
    d_tok, l_tok = _tokens(description), _tokens(location)
    matches = []
    for t in existing:
        if t["Category"] != category:
            continue
        score = 0.6 * _jaccard(d_tok, _tokens(t["Description"])) + 0.4 * _jaccard(l_tok, _tokens(t["Location"]))
        if score >= 0.3:
            matches.append({"id": t["Complaint ID"], "similarity": round(min(score * 1.4, 0.97), 2),
                            "location": t["Location"], "description": t["Description"]})
    return sorted(matches, key=lambda m: m["similarity"], reverse=True)[:3]


# --------------------------------------------------------------------------- #
# Seed data
# --------------------------------------------------------------------------- #
# (description, category, severity, location, days ago, status, people, nearby place)
SEED = [
    ("Live electric wire hanging from a pole near the bus stop, sparking in the rain", "Electricity", "Critical", "Indiranagar 100 Feet Road", 0, "Pending", 300, None),
    ("Huge pothole on the main road, two bikers fell this morning", "Roads", "Critical", "Outer Ring Road, Marathahalli", 1, "In Progress", 500, None),
    ("Open manhole without a cover near the government school gate", "Drainage", "Critical", "Jayanagar 4th Block", 1, "Pending", 400, "school"),
    ("Transformer humming loudly and sparking at night", "Electricity", "Critical", "Kalyan Nagar", 2, "Pending", 350, None),
    ("Garbage not collected for 6 days, foul smell near the market", "Waste", "High", "Malleshwaram 8th Cross", 2, "Pending", 150, None),
    ("Water pipe burst, road flooded and no supply to the street", "Water", "High", "Koramangala 5th Block", 2, "In Progress", 200, None),
    ("Streetlights not working along the whole stretch, very dark at night", "Electricity", "Medium", "HSR Layout Sector 2", 3, "Pending", 80, None),
    ("Large tree branch fell and is blocking half of the road", "Trees", "High", "Rajajinagar 2nd Block", 3, "In Progress", 120, None),
    ("Drain overflowing into houses after the rain", "Drainage", "High", "BTM Layout 2nd Stage", 4, "Pending", 90, None),
    ("ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿ ಇದೆ, ಶಾಲೆಯ ಹತ್ತಿರ", "Roads", "High", "Yelahanka New Town", 4, "Pending", 250, "school"),
    ("कचरा सड़क किनारे जमा है, कई दिनों से नहीं उठा", "Waste", "Medium", "Whitefield, ITPL Main Road", 5, "Pending", 60, None),
    ("Low water pressure every morning for the past week", "Water", "Low", "Banashankari 2nd Stage", 5, "Resolved", 40, None),
    ("Overflowing dustbin at the park entrance", "Waste", "Low", "Hebbal Kempapura", 6, "Resolved", 25, None),
    ("Dead tree leaning over a compound wall, may fall", "Trees", "Medium", "Basavanagudi", 6, "Pending", 30, None),
    ("Pothole near the hospital gate is delaying ambulances", "Roads", "High", "Sarjapur Road, near hospital", 7, "In Progress", 600, "hospital"),
    ("Sewage water mixing with the drinking water supply", "Water", "Critical", "Shivajinagar", 7, "In Progress", 800, None),
    ("Streetlight flickering near the park", "Electricity", "Low", "Vijayanagar", 8, "Resolved", 20, None),
    ("Road surface sinking near a metro pillar, cracks widening", "Roads", "High", "Jalahalli", 8, "Pending", 350, None),
    ("ನೀರಿನ ಪೈಪ್ ಒಡೆದಿದೆ, ನೀರು ವ್ಯರ್ಥವಾಗುತ್ತಿದೆ", "Water", "Medium", "Kengeri", 9, "Resolved", 70, None),
    ("बिजली का खंभा झुका हुआ है, गिरने का खतरा है", "Electricity", "High", "Yeshwanthpur", 9, "Pending", 200, None),
    ("Garbage being burned near an apartment, smoke entering homes", "Waste", "High", "Bellandur", 10, "In Progress", 400, None),
    ("Blocked storm drain, water logging after every rain", "Drainage", "Medium", "Domlur", 11, "Resolved", 120, None),
    ("Fallen tree was cleared but branches still lie on the footpath", "Trees", "Low", "Cox Town", 12, "Resolved", 15, None),
    ("Footpath tiles broken near the bus stand", "Roads", "Low", "Majestic", 13, "Pending", 50, None),
]


def _ticket(**kw) -> dict:
    return {c: kw.get(c) for c in TICKET_COLUMNS + EXTRA_COLUMNS}


def _seed() -> list[dict]:
    now = datetime.now().replace(second=0, microsecond=0)
    rows = []
    for i, (desc, cat, sev, loc, days, status, people, place) in enumerate(SEED):
        school, hospital = place == "school", place == "hospital"
        score, _, _ = _impact(sev, people, school, hospital)
        rows.append(_ticket(**{
            "Description": desc, "Category": cat, "Severity": sev,
            "Reason": _reason(sev, school, hospital), "Department": DEPARTMENTS[cat],
            "Location": loc + (", Bengaluru" if "," not in loc else ""),
            "Date": now - timedelta(days=days, hours=(i * 7) % 20, minutes=(i * 13) % 60),
            "Status": status, "Impact": score,
            "Summary": f"{ISSUE_LABEL[cat]} reported at {loc}.",
            "Action": _action(cat, sev), "Language": _detect_language(desc), "People": people,
        }))
    rows.sort(key=lambda r: r["Date"])
    for n, r in enumerate(rows, 1):
        r["Complaint ID"] = f"CL-{now.year}-{n:04d}"
    return rows


def _ensure() -> list[dict]:
    if "_tickets" not in st.session_state:
        st.session_state["_tickets"] = _seed()
    return st.session_state["_tickets"]


# --------------------------------------------------------------------------- #
# Public API (same shape as backend_api.py)
# --------------------------------------------------------------------------- #
def submit_complaint(text: str, language: str, location: str, image_bytes=None,
                     people_affected: int = 0, near_school: bool = False,
                     near_hospital: bool = False) -> dict:
    tickets = _ensure()
    people = int(people_affected or 0)
    category = _classify(text)
    sev, reason = _severity(text, category, people, near_school, near_hospital)
    score, band, breakdown = _impact(sev, people, near_school, near_hospital)
    dups = _duplicates(text, location, category, tickets)
    now = datetime.now().replace(second=0, microsecond=0)
    complaint_id = f"CL-{now.year}-{len(tickets) + 1:04d}"
    detected = _detect_language(text)
    summary = f"{ISSUE_LABEL[category]} reported near {location.strip()}."

    tickets.append(_ticket(**{
        "Complaint ID": complaint_id, "Description": text.strip(), "Category": category,
        "Severity": sev, "Reason": reason, "Department": DEPARTMENTS[category],
        "Location": location.strip(), "Date": now, "Status": "Pending", "Impact": score,
        "Summary": summary, "Action": _action(category, sev), "Language": detected, "People": people,
    }))

    return {
        "complaint_id": complaint_id, "description": text.strip(), "location": location.strip(),
        "category": category, "severity": sev, "severity_reason": reason, "summary": summary,
        "department": DEPARTMENTS[category], "suggested_action": _action(category, sev),
        "language_detected": detected, "impact_score": score, "impact_band": band,
        "impact_breakdown": breakdown, "duplicates": dups, "status": "Pending",
        "created_at": now, "image_bytes": image_bytes,
    }


def get_tickets() -> pd.DataFrame:
    return pd.DataFrame(_ensure(), columns=TICKET_COLUMNS + EXTRA_COLUMNS)


def set_status(complaint_id: str, new_status: str) -> None:
    for t in _ensure():
        if t["Complaint ID"] == complaint_id:
            t["Status"] = new_status
            return
