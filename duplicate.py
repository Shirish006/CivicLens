"""duplicate.py - Duplicate complaint detection engine for CivicLens.
Uses TF-IDF and Cosine Similarity to detect similar civic grievances within
the same category, combining description text and location similarity.
Never deletes duplicates; returns reference matches to inform citizens and officers.
"""
import re
from typing import Any, Dict, List
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _compute_location_similarity(loc1: str, loc2: str) -> float:
    """Compute token-level Jaccard similarity between two location strings."""
    if not loc1 or not loc2:
        return 0.0

    tokens1 = set(re.findall(r"\w+", loc1.lower()))
    tokens2 = set(re.findall(r"\w+", loc2.lower()))

    # Ignore generic city names
    stop_tokens = {"bengaluru", "bangalore", "near", "road", "cross", "main", "opp", "opposite"}
    tokens1 = tokens1 - stop_tokens
    tokens2 = tokens2 - stop_tokens

    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return float(intersection) / float(union) if union > 0 else 0.0


def _token_jaccard(t1: str, t2: str) -> float:
    """Compute token Jaccard similarity between two complaint descriptions."""
    w1 = set(re.findall(r"\w+", (t1 or "").lower()))
    w2 = set(re.findall(r"\w+", (t2 or "").lower()))
    stop = {"the", "a", "an", "is", "in", "at", "of", "and", "or", "for", "with", "near", "to", "this", "it", "on", "from", "are", "be"}
    w1 = w1 - stop
    w2 = w2 - stop
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def check_duplicates(
    new_text: str,
    new_category: str,
    new_location: str,
    existing_df: pd.DataFrame,
    threshold: float = 0.30,
) -> List[Dict[str, Any]]:
    """Check if a new complaint is a potential duplicate of existing complaints.

    Args:
        new_text: English text (or translation) of the new complaint.
        new_category: Category (e.g. 'Roads', 'Waste').
        new_location: Location string.
        existing_df: DataFrame of existing complaints in the database.
        threshold: Combined similarity threshold (0.0 to 1.0) to flag as duplicate.

    Returns:
        List of matching complaint dictionaries with match percentage and details.
    """
    if existing_df is None or existing_df.empty:
        return []

    # 1. Filter existing complaints to the same category (case-insensitive)
    cat_col = "category" if "category" in existing_df.columns else "Category"
    category_df = existing_df[existing_df[cat_col].astype(str).str.strip().str.lower() == str(new_category).strip().lower()].copy()
    if category_df.empty or len(category_df) < 1:
        return []

    # 2. Extract texts (prefer english_translation, fallback to description)
    existing_texts = []
    for _, row in category_df.iterrows():
        text = str(row.get("english_translation") or row.get("description") or "").strip()
        existing_texts.append(text)

    all_texts = existing_texts + [str(new_text).strip()]

    # TF-IDF Cosine Similarity on descriptions
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        text_sims = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]
    except Exception:
        text_sims = [0.0] * len(existing_texts)

    matches = []
    for idx, (_, row) in enumerate(category_df.iterrows()):
        t_sim = float(text_sims[idx])
        j_sim = _token_jaccard(new_text, existing_texts[idx])
        t_best = max(t_sim, j_sim)
        l_sim = _compute_location_similarity(new_location, str(row.get("location", "")))

        # Weighted combination: 60% text description + 40% location
        combined_sim = (0.60 * t_best) + (0.40 * l_sim)

        if combined_sim >= threshold or t_best >= 0.50 or (l_sim >= 0.60 and t_best >= 0.25):
            pct = int(round(min(1.0, max(combined_sim * 1.15, t_best)) * 100))
            cid = str(row.get("id") or row.get("Complaint ID", ""))
            matches.append(
                {
                    "id": cid,
                    "similarity_pct": pct,
                    "text_similarity_pct": int(round(t_best * 100)),
                    "location_similarity_pct": int(round(l_sim * 100)),
                    "location": str(row.get("location", "Not specified")),
                    "summary": str(row.get("summary") or row.get("description") or "")[:100],
                    "status": str(row.get("status", "Pending")),
                    "created_at": str(row.get("created_at", "")),
                }
            )

    # Sort matches by highest similarity first
    matches.sort(key=lambda x: x["similarity_pct"], reverse=True)
    return matches


if __name__ == "__main__":
    print("=== Testing duplicate.py Standalone ===")

    dummy_data = [
        {
            "id": "CL-20261121-0001",
            "category": "Roads",
            "english_translation": "Deep dangerous pothole on 100 Feet Road Indiranagar causing vehicles to skid.",
            "description": "Deep dangerous pothole on 100 Feet Road Indiranagar",
            "location": "100 Feet Road, Indiranagar",
            "summary": "Deep pothole causing skidding",
            "status": "In Progress",
            "created_at": "2026-11-21 10:00:00",
        },
        {
            "id": "CL-20261121-0002",
            "category": "Waste",
            "english_translation": "Garbage dump overflowing on Sampige road",
            "description": "Garbage dump overflowing on Sampige road",
            "location": "Sampige Road, Malleshwaram",
            "summary": "Garbage dump overflowing",
            "status": "Pending",
            "created_at": "2026-11-21 10:30:00",
        },
    ]
    df = pd.DataFrame(dummy_data)

    new_complaint = "Huge pothole on 100ft road Indiranagar, two-wheelers are falling down."
    matches = check_duplicates(
        new_text=new_complaint,
        new_category="Roads",
        new_location="100 Feet Road Indiranagar",
        existing_df=df,
    )

    print(f"Duplicate matches found: {len(matches)}")
    for m in matches:
        print(f"Matched Ticket: {m['id']} | Similarity: {m['similarity_pct']}% | Location: {m['location']}")
