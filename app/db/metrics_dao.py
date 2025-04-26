from datetime import datetime
from google.cloud import firestore
from app.db.firestore_helper import get_collection

metrics_ref = get_collection("metrics").document("summary")
daily_ref = get_collection("daily_stats")

def increment_metric(field_name: str):
    metrics_ref.set({field_name: firestore.Increment(1), "last_updated": datetime.utcnow().isoformat()}, merge=True)

def increment_daily(field_name: str):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    ref = daily_ref.document(today)
    ref.set({field_name: firestore.Increment(1), "date": today}, merge=True)
    
def decrement_metric(field_name: str):
    metrics_ref.set({field_name: firestore.Increment(-1), "last_updated": datetime.utcnow().isoformat()}, merge=True)

def get_summary_metrics():
    doc = metrics_ref.get()
    return doc.to_dict() if doc.exists else {}

def get_daily_metrics(date_str: str):
    doc = daily_ref.document(date_str).get()
    return doc.to_dict() if doc.exists else {}

def get_all_daily_metrics(limit=30):
    return [doc.to_dict() for doc in daily_ref.order_by("date", direction=firestore.Query.DESCENDING).limit(limit).stream()]

