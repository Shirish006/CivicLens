"""routing.py - Deterministic rule-based municipal department router for CivicLens.
Maps classified categories to official municipal departments.
This rule-based logic is the single source of truth for department assignments.
"""
from typing import Dict

# Authoritative municipal department mapping
DEPARTMENT_ROUTING_RULES: Dict[str, str] = {
    "Roads": "Road Maintenance Department",
    "Waste": "Solid Waste Management Department",
    "Water": "Water Supply Department",
    "Electricity": "Electrical Department",
    "Trees": "Horticulture Department",
    "Drainage": "Drainage Department",
}


def get_official_department(category: str) -> str:
    """Return the authoritative municipal department for a given complaint category.

    Args:
        category: Classified complaint category (Roads, Waste, Water, Electricity, Trees, Drainage)

    Returns:
        Official department name string.
    """
    if not category:
        return "General Municipal Administration"

    clean_category = category.strip().capitalize()
    return DEPARTMENT_ROUTING_RULES.get(clean_category, "General Municipal Administration")


if __name__ == "__main__":
    print("=== Testing Department Routing Engine ===")
    test_categories = ["Roads", "Waste", "Water", "Electricity", "Trees", "Drainage", "Unknown"]

    for cat in test_categories:
        dept = get_official_department(cat)
        print(f"Category: {cat:12} -> Official Department: {dept}")
