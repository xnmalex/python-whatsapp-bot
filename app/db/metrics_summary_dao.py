from app.db.firestore_helper import get_collection
from datetime import datetime
from google.cloud import firestore

summary_ref = get_collection("daily_summary")

def store_daily_summary(summary: dict):
    date_str = summary["date"]
    summary_ref.document(date_str).set(summary)

def get_daily_summary_by_date(date_str):
    doc = summary_ref.document(date_str).get()
    return doc.to_dict() if doc.exists else None

def get_recent_daily_summaries(limit=30):
    return [
        doc.to_dict()
        for doc in summary_ref
            .order_by("date", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
    ]
