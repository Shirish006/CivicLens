"""impact_score.py - Explainable Civic Impact Score Calculator for CivicLens.
Computes a transparent 0-100 score prioritizing civic grievances based on
severity, affected population, and proximity to schools and hospitals.
Clearly distinguishes 'Citizen-reported, unverified' claims from 'Verified by officer' facts.
"""
from typing import Any, Dict, List, Tuple

# Severity baseline point distribution
SEVERITY_POINTS = {
    "Critical": 70,  # Life safety, acute hazard
    "High": 50,      # Serious public health or major transit disruption
    "Medium": 30,    # Substantial localized inconvenience
    "Low": 10,       # Routine or cosmetic maintenance
}


def _get_people_affected_points(count: int) -> int:
    """Map reported citizen count to impact points (0 - 15 points)."""
    if count <= 0:
        return 0
    elif count < 10:
        return 3
    elif count < 50:
        return 7
    elif count < 200:
        return 11
    else:
        return 15


def calculate_impact_score(
    severity: str,
    people_affected: int = 0,
    near_school: bool = False,
    near_hospital: bool = False,
    inputs_verified: bool = False,
) -> Tuple[int, List[Dict[str, Any]], str]:
    """Calculate an explainable impact score between 0 and 100.

    Args:
        severity: One of Critical, High, Medium, Low.
        people_affected: Estimated number of citizens impacted.
        near_school: Whether issue is in proximity to educational institute.
        near_hospital: Whether issue is in proximity to medical facility.
        inputs_verified: False = 'Citizen-reported, unverified', True = 'Verified by officer'.

    Returns:
        Tuple of (final_score: int, breakdown: List[Dict], band_label: str)
    """
    clean_sev = severity.strip().capitalize() if severity else "Medium"
    sev_points = SEVERITY_POINTS.get(clean_sev, 30)

    people_count = max(0, int(people_affected or 0))
    people_points = _get_people_affected_points(people_count)

    school_points = 8 if near_school else 0
    hospital_points = 7 if near_hospital else 0

    verification_status = "Verified by officer" if inputs_verified else "Citizen-reported, unverified"

    breakdown = []

    # 1. Base Severity Points
    breakdown.append(
        {
            "factor": "Grievance Severity",
            "detail": f"{clean_sev} risk classification",
            "points": sev_points,
            "status": "AI / Municipal Standards",
        }
    )

    # 2. Population Impact
    if people_count > 0:
        breakdown.append(
            {
                "factor": "Estimated Citizens Impacted",
                "detail": f"~{people_count} citizens affected daily",
                "points": people_points,
                "status": verification_status,
            }
        )

    # 3. School Proximity
    if near_school:
        breakdown.append(
            {
                "factor": "School / College Proximity",
                "detail": "Adjacent to educational institution",
                "points": school_points,
                "status": verification_status,
            }
        )

    # 4. Hospital Proximity
    if near_hospital:
        breakdown.append(
            {
                "factor": "Healthcare Facility Proximity",
                "detail": "Adjacent to hospital or clinical center",
                "points": hospital_points,
                "status": verification_status,
            }
        )

    # Total score calculation capped strictly at 100
    raw_total = sev_points + people_points + school_points + hospital_points
    final_score = min(100, max(0, raw_total))

    # Priority Band Assignment
    if final_score >= 70:
        band = "Urgent"
    elif final_score >= 40:
        band = "Elevated"
    else:
        band = "Routine"

    return final_score, breakdown, band


def get_band_color(band: str) -> str:
    """Return theme color for impact score priority band."""
    return {
        "Urgent": "#EF4444",   # Red
        "Elevated": "#F59E0B", # Amber
        "Routine": "#10B981",  # Green
    }.get(band, "#13A89E")


if __name__ == "__main__":
    print("=== Testing impact_score.py Standalone ===")

    # Test 1: Unverified High Severity with School & People
    score1, b1, band1 = calculate_impact_score(
        severity="High",
        people_affected=120,
        near_school=True,
        near_hospital=False,
        inputs_verified=False,
    )
    print(f"Test 1 Score: {score1}/100 [{band1}]")
    for item in b1:
        print(f"  + {item['points']:2} pts | {item['factor']}: {item['detail']} ({item['status']})")

    # Test 2: Verified Critical with Hospital
    score2, b2, band2 = calculate_impact_score(
        severity="Critical",
        people_affected=300,
        near_school=False,
        near_hospital=True,
        inputs_verified=True,
    )
    print(f"\nTest 2 Score: {score2}/100 [{band2}]")
    for item in b2:
        print(f"  + {item['points']:2} pts | {item['factor']}: {item['detail']} ({item['status']})")
