"""Shared constants. Single source of truth for categories, severities and routing."""

CATEGORIES = ["Roads", "Waste", "Water", "Electricity", "Trees", "Drainage"]

DEPARTMENTS = {
    "Roads": "Road Maintenance Department",
    "Waste": "Solid Waste Management Department",
    "Water": "Water Supply Department",
    "Electricity": "Electrical Department",
    "Trees": "Horticulture Department",
    "Drainage": "Drainage Department",
}

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]
STATUS_ORDER = ["Pending", "In Progress", "Resolved"]

LANGUAGES = ["English", "ಕನ್ನಡ (Kannada)", "हिन्दी (Hindi)"]

TICKET_COLUMNS = [
    "Complaint ID", "Description", "Category", "Severity", "Reason",
    "Department", "Location", "Date", "Status",
]
