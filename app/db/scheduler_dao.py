from datetime import datetime, timezone
from app.db.firestore_helper import get_collection
from google.cloud.firestore_v1 import FieldFilter

schedulers_ref = get_collection("message_schedulers")

# Create new scheduled message
def create_schedule(app_id, name, platform, content, send_at, recipients):
    doc_ref = schedulers_ref.document()
    now = datetime.now(timezone.utc)
    schedule = {
        "schedule_id": doc_ref.id,
        "app_id": app_id,
        "name": name,
        "platform": platform,
        "content": content,
        "send_at": send_at,  # Expected in ISO format
        "recipients": recipients,
        "status": "scheduled",
        "created_at": now,
        "updated_at": now
    }
    doc_ref.set(schedule)
    return schedule

# List schedules by app_id
def list_schedules_by_app_id(app_id, limit=20, start_after=None):
    query = schedulers_ref.where(filter=FieldFilter("app_id", "==", app_id)).order_by("send_at").limit(limit)
    if start_after:
        query = query.start_after({"send_at": start_after})
    docs = query.stream()
    return [doc.to_dict() for doc in docs]

# Get schedule by ID
def get_schedule_by_id(schedule_id):
    doc = schedulers_ref.document(schedule_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()

# Update schedule
def update_schedule(schedule_id, updates):
    doc_ref = schedulers_ref.document(schedule_id)
    if not doc_ref.get().exists:
        return None
    updates["updated_at"] = datetime.now(timezone.utc)
    doc_ref.update(updates)
    return True

# Delete schedule
def delete_schedule(schedule_id):
    doc_ref = schedulers_ref.document(schedule_id)
    if not doc_ref.get().exists:
        return None
    doc_ref.delete()
    return True

def get_due_schedules(current_time_iso):
    query = schedulers_ref \
        .where(filter=FieldFilter("status", "==", "scheduled")) \
        .where(filter=FieldFilter("send_at", "<=", current_time_iso)) \
        .order_by("send_at") \
        .limit(50)
    docs = query.stream()
    return [doc.to_dict() for doc in docs]

