"""ai_analysis.py - Gemini Multimodal AI Complaint Triage Engine.
Extracts structured JSON (category, severity, department, translation, summary)
with an offline keyword-based fallback analyzer.
"""
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, Literal, Optional
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel

# Logger setup
logger = logging.getLogger(__name__)

# Valid taxonomy
VALID_CATEGORIES = ["Roads", "Waste", "Water", "Electricity", "Trees", "Drainage"]
VALID_SEVERITIES = ["Low", "Medium", "High", "Critical"]


class ComplaintSchema(BaseModel):
    category: Literal["Roads", "Waste", "Water", "Electricity", "Trees", "Drainage"]
    severity: Literal["Low", "Medium", "High", "Critical"]
    severity_reason: str
    summary: str
    recommended_department: str
    suggested_action: str
    detected_language: str
    english_translation: str


SYSTEM_PROMPT = """You are CivicLens, an expert AI triage officer for municipal citizen complaints.
Analyze the complaint text and (if provided) the accompanying image.

TAXONOMY & GUIDELINES:
1. Category must be strictly one of:
   - 'Roads' (potholes, asphalt damage, broken footpaths, speed breakers)
   - 'Waste' (garbage dumping, overflowing bins, dead animals, litter)
   - 'Water' (pipeline bursts, contaminated supply, low pressure, tanker issues)
   - 'Electricity' (exposed live wires, broken streetlights, transformer fire risk)
   - 'Trees' (fallen branches, uprooted trees, blocking traffic/wires)
   - 'Drainage' (overflowing sewage, open manholes, blocked storm drains, waterlogging)

2. Severity must be strictly one of:
   - 'Critical': Immediate danger to human life or safety (e.g. exposed live wire, open manhole, major flood risk, blocked hospital route).
   - 'High': Serious disruption or significant public health/environmental hazard.
   - 'Medium': Substantial public inconvenience or localized disruption.
   - 'Low': Minor cosmetic or routine maintenance issue.

3. Language:
   - Identify the source language (English, Kannada, or Hindi).
   - Accurately translate non-English complaints to standard English for city officials.
   - Keep summary under 25 words.
"""


def _normalize_analysis(data: Dict[str, Any], default_desc: str) -> Dict[str, Any]:
    """Validate and normalize fields to guarantee adherence to taxonomy."""
    cat = data.get("category", "").capitalize()
    if cat not in VALID_CATEGORIES:
        cat_matches = [c for c in VALID_CATEGORIES if c.lower() in cat.lower()]
        cat = cat_matches[0] if cat_matches else "Roads"

    sev = data.get("severity", "").capitalize()
    if sev not in VALID_SEVERITIES:
        sev = "Medium"

    return {
        "category": cat,
        "severity": sev,
        "severity_reason": data.get("severity_reason", "Assessed according to municipal safety protocols.").strip(),
        "summary": data.get("summary", default_desc[:120]).strip(),
        "recommended_department": data.get("recommended_department", f"{cat} Department").strip(),
        "suggested_action": data.get("suggested_action", "Dispatch inspection team to assess field conditions.").strip(),
        "detected_language": data.get("detected_language", "English").strip(),
        "english_translation": data.get("english_translation", default_desc).strip(),
    }


def _generate_fallback_translation(description: str, category: str, lang: str, location: str) -> str:
    """Generate a clean English translation during offline/fallback mode."""
    if lang == "English":
        return description.strip()

    translations = {
        "Roads": "Large pothole and damaged road surface causing commuter hazards and traffic delays. Repair requested.",
        "Waste": "Overflowing garbage dump and uncollected waste creating foul stench and stray dog hazard.",
        "Water": "Drinking water pipeline leak/burst with thousands of liters of clean water getting wasted.",
        "Electricity": "Faulty electrical wiring or non-functional streetlights posing severe shock and safety risks.",
        "Trees": "Uprooted tree or fallen large branches blocking vehicular movement and pedestrian access.",
        "Drainage": "Blocked storm drainage or open manhole creating severe overflow and safety hazard.",
    }
    base = translations.get(category, f"Civic complaint regarding {category.lower()} issue.")
    if location:
        return f"{base} (Location: {location})"
    return base


def analyze_with_fallback(description: str, location: str = "") -> Dict[str, Any]:
    """Offline keyword-based fallback analyzer for English, Kannada, and Hindi."""
    text_lower = f"{description} {location}".lower()

    # Category keyword matching
    cat_scores = {c: 0 for c in VALID_CATEGORIES}

    road_keywords = ["pothole", "road", "asphalt", "tar", "footpath", "ಗುಂಡಿ", "ರಸ್ತೆ", "ಖಡ್ಡಾ", "सड़क", "गड्ढा", "मार्ग"]
    waste_keywords = ["garbage", "trash", "waste", "bin", "dump", "smell", "ಕಸ", "ತ್ಯಾಜ್ಯ", "ದುರ್ನಾತ", "कचरा", "कूड़ा", "बदबू"]
    water_keywords = ["water", "leak", "pipe", "pipeline", "drinking", "ನೀರು", "ಸೋರಿಕೆ", "ಪೈಪ್", "पानी", "पाइप", "लीक", "जल"]
    elec_keywords = ["electric", "wire", "streetlight", "light", "spark", "current", "ವಿದ್ಯುತ್", "ತಂತಿ", "ದೀಪ", "बिजली", "तार", "लाइट"]
    tree_keywords = ["tree", "branch", "fallen tree", "ಮರ", "ರೆಂಬೆ", "पेड़", "शाखा", "वृक्ष"]
    drain_keywords = ["drain", "drainage", "sewage", "manhole", "gutter", "ಚರಂಡಿ", "ಮ್ಯಾನ್‌ಹೋಲ್", "ನಾಲೆ", "नाली", "सीवर", "मैनहोल"]

    for kw in road_keywords:
        if kw in text_lower:
            cat_scores["Roads"] += 2
    for kw in waste_keywords:
        if kw in text_lower:
            cat_scores["Waste"] += 2
    for kw in water_keywords:
        if kw in text_lower:
            cat_scores["Water"] += 2
    for kw in elec_keywords:
        if kw in text_lower:
            cat_scores["Electricity"] += 2
    for kw in tree_keywords:
        if kw in text_lower:
            cat_scores["Trees"] += 2
    for kw in drain_keywords:
        if kw in text_lower:
            cat_scores["Drainage"] += 2

    best_cat = max(cat_scores, key=cat_scores.get)
    if cat_scores[best_cat] == 0:
        best_cat = "Roads"

    # Severity keyword matching
    critical_keywords = ["accident", "danger", "emergency", "live wire", "open manhole", "death", "die", "sparking",
                         "ಅಪಘಾತ", "ಅಪಾಯ", "ತೆರೆದ ಮ್ಯಾನ್‌ಹೋಲ್", "ದುರ್ಘಟನೆ", "करंट", "दुर्घटना", "खतरा", "खुला मैनहोल"]
    high_keywords = ["burst", "overflow", "flooding", "blocked", "hospital", "school", "ತುಂಬಿ", "ಸೋರಿಕೆ", "बाढ़", "जाम"]

    if any(k in text_lower for k in critical_keywords):
        severity = "Critical"
        reason = "Immediate safety hazard or risk of injury detected via priority keywords."
    elif any(k in text_lower for k in high_keywords):
        severity = "High"
        reason = "Significant public disruption or potential health hazard detected."
    else:
        severity = "Medium"
        reason = "Standard maintenance grievance requiring departmental inspection."

    # Language detection
    kannada_chars = re.findall(r"[\u0C80-\u0CFF]", description)
    hindi_chars = re.findall(r"[\u0900-\u097F]", description)
    if len(kannada_chars) > len(description) * 0.1:
        lang = "Kannada"
    elif len(hindi_chars) > len(description) * 0.1:
        lang = "Hindi"
    else:
        lang = "English"

    translated_text = _generate_fallback_translation(description, best_cat, lang, location)
    summary_text = translated_text if lang != "English" else description[:120].strip()

    return {
        "category": best_cat,
        "severity": severity,
        "severity_reason": reason,
        "summary": summary_text,
        "recommended_department": f"{best_cat} Department",
        "suggested_action": f"Dispatch field crew to inspect {best_cat.lower()} issue at reported site.",
        "detected_language": lang,
        "english_translation": translated_text,
        "analysis_source": "fallback",
        "fallback_note": "AI unavailable – keyword fallback analysis used",
    }


def analyze_complaint(description: str, location: str = "", image_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a complaint using Gemini Flash or fallback safely."""
    # Always re-read .env with override so changes apply immediately
    dotenv_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=True)

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    if not api_key or "your_key_here" in api_key:
        logger.warning("No Gemini API key found. Using fallback analysis.")
        return analyze_with_fallback(description, location)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt_text = (
            f"{SYSTEM_PROMPT}\n\n"
            f"CITIZEN COMPLAINT DATA:\n"
            f"Location: {location}\n"
            f"Complaint Text: {description}\n"
        )

        contents = [prompt_text]

        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                contents.append(img)
            except Exception as img_err:
                logger.warning(f"Failed to open image {image_path}: {img_err}")

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ComplaintSchema,
            temperature=0.1,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

        raw_json = json.loads(response.text)
        result = _normalize_analysis(raw_json, description)
        result["analysis_source"] = "gemini"
        result["fallback_note"] = None
        return result

    except Exception as e:
        logger.error(f"Gemini API analysis failed: {e}. Falling back to keyword engine.")
        fallback = analyze_with_fallback(description, location)
        fallback["fallback_note"] = f"AI unavailable ({type(e).__name__}) – fallback analysis used"
        return fallback
