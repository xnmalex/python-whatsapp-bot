from datetime import datetime
from app.db.firestore_helper import get_collection
from google.cloud.firestore_v1 import FieldFilter
from app.db.thread_dao import upsert_thread_last_message, get_threads_by_app_id

messages_ref = get_collection("messages")

# Save a user, assistant, or human agent message to Firestore
def save_message(**kwargs):
    now = datetime.utcnow().isoformat()

    message_data = {
        "user_id": kwargs.get("user_id"),
        "app_id": kwargs.get("app_id"),
        "platform": kwargs.get("platform"),
        "chat_id": kwargs.get("chat_id"),
        "direction": kwargs.get("direction", "left"),
        "role": kwargs.get("role", "user"),
        "content": kwargs.get("content"),
        "message_type": kwargs.get("message_type"),
        "file_url": kwargs.get("file_url"),
        "created_at": now,
        "updated_at": now
    }

    if "thread_id" in kwargs:
        message_data["thread_id"] = kwargs["thread_id"]

    doc_ref = messages_ref.document()
    message_data["message_id"] = doc_ref.id
    doc_ref.set(message_data)
    
    
    # Update latest thread info
    upsert_thread_last_message(
        chat_id=message_data["chat_id"],
        app_id=message_data["app_id"],
        content=message_data["content"],
        platform=message_data["platform"],
        role=message_data["role"],
        message_type=message_data["message_type"],
        file_url=message_data["file_url"]
    )
    return message_data

def update_message_by_thread(thread_id: str, updates: dict):
    """
    Update a message document by its thread_id.
    """
    messages = messages_ref.where(filter=FieldFilter("thread_id", "==", thread_id)).limit(1).stream()
    for msg in messages:
        updates["updated_at"] = datetime.utcnow().isoformat()
        messages_ref.document(msg.id).update(updates)
        return True
    return False

# Fetch messages by user (optional utility)
def get_messages_by_app(app_id, limit=20):
    query = messages_ref.where(filter=FieldFilter("app_id", "==", app_id)).order_by("created_at", direction="DESCENDING").limit(limit)
    return [doc.to_dict() for doc in query.stream()]

# Get messages for a given chat ID with pagination
def get_messages_by_chat_id(chat_id, limit=20, start_after=None):
    query = messages_ref.where(filter=FieldFilter("chat_id", "==", chat_id)).order_by("created_at", direction="DESCENDING").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    messages = query.stream()
    return [msg.to_dict() for msg in messages]

# Get chat thread summaries for a given app ID with pagination
def get_message_threads_by_app_id(app_id, limit=20, start_after=None):
     return get_threads_by_app_id(app_id=app_id, limit=limit, start_after=start_after)