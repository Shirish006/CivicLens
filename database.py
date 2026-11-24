"""database.py - SQLite storage engine for CivicLens.
Manages schema initialization, sequential ID generation (CL-YYYYMMDD-XXXX),
CRUD operations, Pandas DataFrame exports, and demo data seeding.
Includes geospatial coordinates (latitude, longitude) for map visualization.
"""
from datetime import datetime
import json
import re
import sqlite3
from typing import Any, Dict, List, Optional
import pandas as pd
from impact_score import calculate_impact_score

DB_FILE = "civiclens.db"


def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """Return an SQLite connection with row factory configured."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_FILE) -> None:
    """Initialize the complaints table schema if it does not already exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            english_translation TEXT,
            language TEXT,
            category TEXT,
            severity TEXT,
            severity_reason TEXT,
            summary TEXT,
            department TEXT,
            suggested_action TEXT,
            location TEXT,
            latitude REAL DEFAULT 12.9716,
            longitude REAL DEFAULT 77.5946,
            image_path TEXT,
            people_affected INTEGER DEFAULT 0,
            near_school INTEGER DEFAULT 0,
            near_hospital INTEGER DEFAULT 0,
            inputs_verified INTEGER DEFAULT 0,
            impact_score INTEGER DEFAULT 0,
            impact_breakdown TEXT,
            duplicate_of TEXT DEFAULT '',
            analysis_source TEXT DEFAULT 'gemini',
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        );
        """
    )

    # Ensure latitude and longitude columns exist in existing tables
    try:
        cursor.execute("ALTER TABLE complaints ADD COLUMN latitude REAL DEFAULT 12.9716;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE complaints ADD COLUMN longitude REAL DEFAULT 77.5946;")
    except Exception:
        pass

    conn.commit()
    conn.close()


def generate_complaint_id(db_path: str = DB_FILE) -> str:
    """Generate a sequential unique Complaint ID in format CL-YYYYMMDD-XXXX."""
    date_prefix = datetime.now().strftime("%Y%m%d")
    query_prefix = f"CL-{date_prefix}-%"

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM complaints WHERE id LIKE ? ORDER BY id DESC LIMIT 1;",
        (query_prefix,),
    )
    row = cursor.fetchone()

    if row and row["id"]:
        try:
            last_seq = int(row["id"].split("-")[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = 1
    else:
        new_seq = 1

    conn.close()
    return f"CL-{date_prefix}-{new_seq:04d}"


def insert_complaint(data: Dict[str, Any], db_path: str = DB_FILE) -> str:
    """Insert a new complaint into SQLite using parameterized queries."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    complaint_id = data.get("id") or generate_complaint_id(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO complaints (
            id, description, english_translation, language, category,
            severity, severity_reason, summary, department, suggested_action,
            location, latitude, longitude, image_path, people_affected,
            near_school, near_hospital, inputs_verified, impact_score,
            impact_breakdown, duplicate_of, analysis_source, created_at, status
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?
        );
        """,
        (
            complaint_id,
            data.get("description", ""),
            data.get("english_translation", ""),
            data.get("language", "English"),
            data.get("category", "Roads"),
            data.get("severity", "Medium"),
            data.get("severity_reason", ""),
            data.get("summary", ""),
            data.get("department", "General Municipal Administration"),
            data.get("suggested_action", ""),
            data.get("location", ""),
            float(data.get("latitude", 12.9716) or 12.9716),
            float(data.get("longitude", 77.5946) or 77.5946),
            data.get("image_path", None),
            int(data.get("people_affected", 0) or 0),
            1 if data.get("near_school") else 0,
            1 if data.get("near_hospital") else 0,
            1 if data.get("inputs_verified") else 0,
            int(data.get("impact_score", 0) or 0),
            data.get("impact_breakdown", "[]"),
            data.get("duplicate_of", ""),
            data.get("analysis_source", "gemini"),
            data.get("created_at", now_str),
            data.get("status", "Pending"),
        ),
    )

    conn.commit()
    conn.close()
    return complaint_id


def get_all_complaints(db_path: str = DB_FILE) -> pd.DataFrame:
    """Retrieve all complaints from the database as a Pandas DataFrame."""
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query("SELECT * FROM complaints ORDER BY created_at DESC;", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


def get_complaint_by_id(complaint_id: str, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    """Retrieve a single complaint by its unique ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints WHERE id = ?;", (complaint_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def update_status(complaint_id: str, new_status: str, db_path: str = DB_FILE) -> bool:
    """Update the processing status (Pending, In Progress, Resolved) of a complaint."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE complaints SET status = ? WHERE id = ?;",
        (new_status, complaint_id),
    )
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def update_verification(
    complaint_id: str,
    is_verified: bool,
    new_score: int,
    new_breakdown_json: str,
    db_path: str = DB_FILE,
) -> bool:
    """Update officer verification status and recomputed impact score."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE complaints
        SET inputs_verified = ?, impact_score = ?, impact_breakdown = ?
        WHERE id = ?;
        """,
        (1 if is_verified else 0, new_score, new_breakdown_json, complaint_id),
    )
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


CANONICAL_SEED = [
    ("Live electric wire hanging from a pole near the bus stop, sparking in the rain", "Electricity", "Critical", "Indiranagar 100 Feet Road, Bengaluru", 300, 0, 0, 12.9784, 77.6408),
    ("Huge pothole on the main road, two bikers fell this morning", "Roads", "Critical", "Outer Ring Road, Marathahalli, Bengaluru", 500, 0, 0, 12.9591, 77.6974),
    ("Open manhole without a cover near the government school gate", "Drainage", "Critical", "Jayanagar 4th Block, Bengaluru", 400, 1, 0, 12.9308, 77.5838),
    ("Transformer humming loudly and sparking at night", "Electricity", "Critical", "Kalyan Nagar, Bengaluru", 350, 0, 0, 13.0221, 77.6403),
    ("Garbage not collected for 6 days, foul smell near the market", "Waste", "High", "Malleshwaram 8th Cross, Bengaluru", 150, 0, 0, 13.0031, 77.5643),
    ("Water pipe burst, road flooded and no supply to the street", "Water", "High", "Koramangala 5th Block, Bengaluru", 200, 0, 0, 12.9352, 77.6245),
    ("Streetlights not working along the whole stretch, very dark at night", "Electricity", "Medium", "HSR Layout Sector 2, Bengaluru", 80, 0, 0, 12.9121, 77.6446),
    ("Large tree branch fell and is blocking half of the road", "Trees", "High", "Rajajinagar 2nd Block, Bengaluru", 120, 0, 0, 12.9915, 77.5554),
    ("Drain overflowing into houses after the rain", "Drainage", "High", "BTM Layout 2nd Stage, Bengaluru", 90, 0, 0, 12.9166, 77.6101),
    ("ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿ ಇದೆ, ಶಾಲೆಯ ಹತ್ತಿರ", "Roads", "High", "Yelahanka New Town, Bengaluru", 250, 1, 0, 13.1007, 77.5963),
    ("कचरा सड़क किनारे जमा है, कई दिनों से नहीं उठा", "Waste", "Medium", "Whitefield, ITPL Main Road, Bengaluru", 60, 0, 0, 12.9698, 77.7500),
    ("Low water pressure every morning for the past week", "Water", "Low", "Banashankari 2nd Stage, Bengaluru", 40, 0, 0, 12.9255, 77.5468),
    ("Overflowing dustbin at the park entrance", "Waste", "Low", "Hebbal Kempapura, Bengaluru", 25, 0, 0, 13.0358, 77.5970),
    ("Dead tree leaning over a compound wall, may fall", "Trees", "Medium", "Basavanagudi, Bengaluru", 30, 0, 0, 12.9421, 77.5753),
    ("Pothole near the hospital gate is delaying ambulances", "Roads", "High", "Sarjapur Road, near hospital, Bengaluru", 600, 0, 1, 12.8600, 77.7860),
    ("Sewage water mixing with the drinking water supply", "Water", "Critical", "Shivajinagar, Bengaluru", 800, 0, 0, 12.9857, 77.6057),
    ("Streetlight flickering near the park", "Electricity", "Low", "Vijayanagar, Bengaluru", 20, 0, 0, 12.9719, 77.5306),
    ("Road surface sinking near a metro pillar, cracks widening", "Roads", "High", "Jalahalli, Bengaluru", 350, 0, 0, 13.0537, 77.5401),
    ("ನೀರಿನ ಪೈಪ್ ಒಡೆದಿದೆ, ನೀರು ವ್ಯರ್ಥವಾಗುತ್ತಿದೆ", "Water", "Medium", "Kengeri, Bengaluru", 70, 0, 0, 12.9081, 77.4842),
    ("बिजली का खंभा झुका हुआ है, गिरने का खतरा है", "Electricity", "High", "Yeshwanthpur, Bengaluru", 200, 0, 0, 13.0280, 77.5409),
    ("Garbage being burned near an apartment, smoke entering homes", "Waste", "High", "Bellandur, Bengaluru", 400, 0, 0, 12.9279, 77.6741),
    ("Blocked storm drain, water logging after every rain", "Drainage", "Medium", "Domlur, Bengaluru", 120, 0, 0, 12.9609, 77.6387),
    ("Fallen tree was cleared but branches still lie on the footpath", "Trees", "Low", "Cox Town, Bengaluru", 15, 0, 0, 12.9965, 77.6220),
    ("Footpath tiles broken near the bus stand", "Roads", "Low", "Majestic, Bengaluru", 50, 0, 0, 12.9767, 77.5713),
]


def seed_sample_complaints(db_path: str = DB_FILE) -> int:
    """Seed 24 realistic canonical complaints across Bengaluru wards with coordinates."""
    from routing import get_official_department
    from datetime import timedelta

    now = datetime.now().replace(second=0, microsecond=0)
    count = 0

    for i, (desc, cat, sev, loc, people, school, hospital, lat, lng) in enumerate(CANONICAL_SEED):
        # Determine language
        if re.search(r"[\u0C80-\u0CFF]", desc):
            lang = "Kannada"
            trans = "Large pothole on road near school" if "ಗುಂಡಿ" in desc else "Water pipe broken and leaking"
        elif re.search(r"[\u0900-\u097F]", desc):
            lang = "Hindi"
            trans = "Garbage piled up on roadside" if "कचरा" in desc else "Electric pole bent, danger of falling"
        else:
            lang = "English"
            trans = desc

        score, breakdown, _ = calculate_impact_score(
            severity=sev,
            people_affected=people,
            near_school=bool(school),
            near_hospital=bool(hospital),
            inputs_verified=False,
        )

        ticket_id = f"CL-{now.strftime('%Y%m%d')}-{100 + i:04d}"
        created_time = (now - timedelta(days=i % 7, hours=(i * 3) % 24)).strftime("%Y-%m-%d %H:%M:%S")

        status = "Resolved" if (i % 5 == 0) else ("In Progress" if (i % 3 == 0) else "Pending")

        record = {
            "id": ticket_id,
            "description": desc,
            "english_translation": trans,
            "language": lang,
            "category": cat,
            "severity": sev,
            "severity_reason": f"Urgent assessment for {cat.lower()} grievance requiring municipal inspection.",
            "summary": f"{cat} incident reported at {loc}.",
            "department": get_official_department(cat),
            "suggested_action": f"Dispatch {cat.lower()} maintenance crew with necessary equipment.",
            "location": loc,
            "latitude": lat,
            "longitude": lng,
            "people_affected": people,
            "near_school": school,
            "near_hospital": hospital,
            "inputs_verified": 0,
            "impact_score": score,
            "impact_breakdown": json.dumps(breakdown),
            "duplicate_of": "",
            "analysis_source": "sample_seed",
            "created_at": created_time,
            "status": status,
        }

        # Check if identical record already exists before inserting
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id FROM complaints WHERE description = ? AND location = ? LIMIT 1;", (desc, loc))
        existing = cur.fetchone()
        conn.close()

        if not existing:
            insert_complaint(record, db_path)
            count += 1

    return count
