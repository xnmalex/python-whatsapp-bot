from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from app.db.firestore_helper import get_collection
from google.cloud.firestore_v1 import FieldFilter

metrics_ref = get_collection("metrics").document("summary")
daily_ref = get_collection("daily_stats")
users_ref = get_collection("users")
apps_ref = get_collection("apps")

def increment_metric(field_name: str):
    metrics_ref.set({field_name: firestore.Increment(1), "last_updated": datetime.now(timezone.utc)}, merge=True)

def increment_daily(field_name: str):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    ref = daily_ref.document(today)
    ref.set({field_name: firestore.Increment(1), "date": today}, merge=True)
    
def decrement_metric(field_name: str):
    metrics_ref.set({field_name: firestore.Increment(-1), "last_updated": datetime.now(timezone.utc)}, merge=True)
    
def decrement_daily(field_name: str):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    ref = daily_ref.document(today)
    ref.set({field_name: firestore.Increment(-11), "date": today}, merge=True)

def get_summary_metrics():
    doc = metrics_ref.get()
    return doc.to_dict() if doc.exists else {}

def get_daily_metrics(date_str: str):
    doc = daily_ref.document(date_str).get()
    return doc.to_dict() if doc.exists else {}

def get_all_daily_metrics(date=None, limit=30):
    query = daily_ref.order_by("date", direction=firestore.Query.DESCENDING)

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            
            print(f"target date: {target_date}")
            start_of_day = datetime(target_date.year, target_date.month, target_date.day)
            end_of_day = start_of_day + timedelta(days=2)
            
            print(f"start_of_day date: {start_of_day}")

            query = query.where(filter=FieldFilter("date", ">=", start_of_day)).where(filter=FieldFilter("date", "<", end_of_day))
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")

    return [doc.to_dict() for doc in query.limit(limit).stream()]

def get_today_summary_metrics():
    now = datetime.utcnow()
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=1)

    # Users
    new_users = users_ref \
        .where(filter=FieldFilter("created_at", ">=", start)) \
        .where(filter=FieldFilter("created_at", "<", end)) \
        .where(filter=FieldFilter("role", "==", "user")) \
        .stream()

    new_admins = users_ref \
        .where(filter=FieldFilter("created_at", ">=", start)) \
        .where(filter=FieldFilter("created_at", "<", end)) \
        .where(filter=FieldFilter("role", "==", "admin")) \
        .stream()

    # Apps
    apps_today = list(apps_ref
        .where(filter=FieldFilter("created_at", ">=", start))
        .where(filter=FieldFilter("created_at", "<", end))
        .stream())

    total_apps = len(apps_today)
    whatsapp_bots = sum(1 for app in apps_today if app.to_dict().get("waba_settings"))
    telegram_bots = sum(1 for app in apps_today if app.to_dict().get("telegram_settings"))

    return {
        "date": start.date().isoformat(),
        "new_users": len(list(new_users)),
        "new_admins": len(list(new_admins)),
        "apps_created": total_apps,
        "new_whatsapp_bots": whatsapp_bots,
        "new_telegram_bots": telegram_bots,
    }