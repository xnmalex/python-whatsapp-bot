from datetime import datetime, timezone
from app.db.firestore_helper import get_collection
from google.cloud.firestore_v1 import FieldFilter

threads_ref = get_collection("threads")

# Save or update the last message of a thread (chat_id)
def upsert_thread_last_message(chat_id, app_id, content, platform, role="user", message_type="text", file_url=None):
    now = datetime.now(timezone.utc)
    threads_ref.document(chat_id).set({
        "chat_id": chat_id,
        "app_id": app_id,
        "last_message": content,
        "created_at": now,
        "platform": platform,
        "role": role,
        "message_type": message_type,
        "file_url": file_url
    }, merge=True)

# Get latest threads for an app ID with pagination
def get_threads_by_app_id(app_id, limit=20, start_after=None):
    query = threads_ref.where(filter=FieldFilter("app_id", "==", app_id)).order_by("created_at", direction="DESCENDING").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    docs = query.stream()
    return [doc.to_dict() for doc in docs]
