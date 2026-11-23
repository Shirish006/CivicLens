"""database.py - SQLite storage engine for CivicLens.
Manages schema initialization, sequential ID generation (CL-YYYYMMDD-XXXX),
CRUD operations, Pandas DataFrame exports, and demo data seeding.
Includes geospatial coordinates (latitude, longitude) for map visualization.
"""
from datetime import datetime
import json
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


def seed_sample_complaints(db_path: str = DB_FILE) -> int:
    """Seed realistic sample complaints across all categories with coordinates."""
    raw_samples = [
        {
            "description": "Exposed high-voltage transformer cable sparking onto wet footpath outside primary school. Immediate electrocution risk!",
            "english_translation": "Exposed high-voltage transformer cable sparking onto wet footpath outside primary school. Immediate electrocution risk!",
            "language": "English",
            "category": "Electricity",
            "severity": "Critical",
            "severity_reason": "Live high-voltage electrical hazard in direct contact with public pedestrian pathway.",
            "summary": "Sparking exposed electrical wire near school",
            "department": "Electrical Department",
            "suggested_action": "Emergency power isolation and dispatch linemen crew immediately.",
            "location": "80 Feet Road, Near St. Mary's School, Koramangala",
            "latitude": 12.9352,
            "longitude": 77.6245,
            "people_affected": 250,
            "near_school": 1,
            "near_hospital": 0,
            "status": "In Progress",
            "duplicate_of": "",
        },
        {
            "description": "ರಸ್ತೆಯಲ್ಲಿ ಭಾರಿ ಗಾತ್ರದ ಗುಂಡಿ ಬಿದ್ದಿದ್ದು ದ್ವಿಚಕ್ರ ವಾಹನ ಸವಾರರು ಬಿದ್ದು ಗಾಯಗೊಂಡಿದ್ದಾರೆ. ತಕ್ಷಣ ಡಾಂಬರೀಕರಣ ಮಾಡಿ.",
            "english_translation": "Huge pothole on main road caused two-wheeler riders to fall and get injured. Needs immediate asphalt patching.",
            "language": "Kannada",
            "category": "Roads",
            "severity": "Critical",
            "severity_reason": "Severe road cavity that has already caused active vehicle accidents and bodily injury.",
            "summary": "Severe pothole causing accidents in Malleshwaram",
            "department": "Road Maintenance Department",
            "suggested_action": "Deploy rapid road repair unit with cold-mix asphalt patch.",
            "location": "15th Cross, Sampige Road, Malleshwaram",
            "latitude": 13.0031,
            "longitude": 77.5643,
            "people_affected": 400,
            "near_school": 0,
            "near_hospital": 1,
            "status": "Pending",
            "duplicate_of": "",
        },
        {
            "description": "Big pothole on Sampige road 15th cross, two-wheelers are skidding and traffic is held up.",
            "english_translation": "Big pothole on Sampige road 15th cross, two-wheelers are skidding and traffic is held up.",
            "language": "English",
            "category": "Roads",
            "severity": "High",
            "severity_reason": "Traffic disruption and recurring skidding risk at busy commercial intersection.",
            "summary": "Pothole on 15th Cross Sampige Road",
            "department": "Road Maintenance Department",
            "suggested_action": "Barricade cavity and schedule road surface repair.",
            "location": "15th Cross, Sampige Road, Malleshwaram",
            "latitude": 13.0035,
            "longitude": 77.5648,
            "people_affected": 300,
            "near_school": 0,
            "near_hospital": 0,
            "status": "Pending",
            "duplicate_of": "CL-20261121-0002",
        },
        {
            "description": "मुख्य सड़क पर सीवर का ढक्कन टूटा हुआ है और खुला पड़ा है। रात में कोई भी इसमें गिर सकता है।",
            "english_translation": "Sewer manhole cover is broken and wide open on the main road. Anyone can fall in at night.",
            "language": "Hindi",
            "category": "Drainage",
            "severity": "Critical",
            "severity_reason": "Open manhole on public thoroughfare posing fatal falling hazard.",
            "summary": "Broken open manhole on main road",
            "department": "Drainage Department",
            "suggested_action": "Place safety barricades and install heavy cast-iron replacement cover.",
            "location": "Gandhi Chowk, Sector 4 Main Road",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "people_affected": 180,
            "near_school": 0,
            "near_hospital": 0,
            "status": "Pending",
            "duplicate_of": "",
        },
        {
            "description": "Massive 500mm drinking water main pipeline fractured and gushing clean drinking water, flooding adjacent residential basements.",
            "english_translation": "Massive 500mm drinking water main pipeline fractured and gushing clean drinking water, flooding adjacent residential basements.",
            "language": "English",
            "category": "Water",
            "severity": "High",
            "severity_reason": "Large-scale potable water wastage accompanied by residential basement flooding.",
            "summary": "Drinking water main pipeline burst flooding street",
            "department": "Water Supply Department",
            "suggested_action": "Shut off zonal control valve and excavate to repair fractured collar.",
            "location": "12th Main, 4th Block, Jayanagar",
            "latitude": 12.9308,
            "longitude": 77.5838,
            "people_affected": 350,
            "near_school": 1,
            "near_hospital": 0,
            "status": "In Progress",
            "duplicate_of": "",
        },
        {
            "description": "Garbage dump overflowing onto road for 6 days. Stray cattle and dogs feeding, intense odor and maggots entering homes.",
            "english_translation": "Garbage dump overflowing onto road for 6 days. Stray cattle and dogs feeding, intense odor and maggots entering homes.",
            "language": "English",
            "category": "Waste",
            "severity": "High",
            "severity_reason": "Severe public health and biological hazard due to prolonged municipal solid waste accumulation.",
            "summary": "Rotting garbage overflowing for six days",
            "department": "Solid Waste Management Department",
            "suggested_action": "Dispatch compactors and sanitize bin area with bleaching powder.",
            "location": "BTM Layout 2nd Stage, near Udupi Garden",
            "latitude": 12.9166,
            "longitude": 77.6101,
            "people_affected": 200,
            "near_school": 0,
            "near_hospital": 1,
            "status": "Pending",
            "duplicate_of": "",
        },
        {
            "description": "Large banyan tree branch cracked during thunderstorm, hanging precariously over road and touching cable TV lines.",
            "english_translation": "Large banyan tree branch cracked during thunderstorm, hanging precariously over road and touching cable TV lines.",
            "language": "English",
            "category": "Trees",
            "severity": "High",
            "severity_reason": "Structural failure of heavy tree limb threatening vehicular traffic and utility lines.",
            "summary": "Cracked heavy tree branch hanging over road",
            "department": "Horticulture Department",
            "suggested_action": "Dispatch tree pruning crane team with chainsaws.",
            "location": "Cunningham Road, opposite Indian Express",
            "latitude": 12.9850,
            "longitude": 77.5980,
            "people_affected": 120,
            "near_school": 0,
            "near_hospital": 0,
            "status": "Pending",
            "duplicate_of": "",
        },
    ]

    count = 0
    for s in raw_samples:
        is_verified = (s["status"] == "Resolved")
        score, breakdown, _ = calculate_impact_score(
            severity=s["severity"],
            people_affected=s["people_affected"],
            near_school=bool(s["near_school"]),
            near_hospital=bool(s["near_hospital"]),
            inputs_verified=is_verified,
        )
        s["impact_score"] = score
        s["impact_breakdown"] = json.dumps(breakdown)
        s["inputs_verified"] = 1 if is_verified else 0
        s["analysis_source"] = "sample"

        insert_complaint(s, db_path)
        count += 1

    return count
