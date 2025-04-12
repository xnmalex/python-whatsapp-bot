from datetime import datetime
import uuid
from app.db.firestore_helper import get_collection

messages_ref = get_collection("messages")

# Save a user message (text or image) to Firestore
def save_message(user_id, app_id, platform, chat_id, content, message_type="text", file_url=None, thread_id=None, assistant_reply=None):
    message_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    message_data = {
        "message_id": message_id,
        "user_id": user_id,
        "app_id": app_id,
        "platform": platform,
        "chat_id": chat_id,
        "content": content,
        "message_type": message_type,
        "file_url": file_url,
        "thread_id": thread_id,
        "assistant_reply": assistant_reply,
        "created_at": now,
        "updated_at": now
    }

    messages_ref.document(message_id).set(message_data)
    return message_data

def update_message_by_thread(thread_id: str, updates: dict):
    """
    Update a message document by its thread_id.
    """
    messages = messages_ref.where("thread_id", "==", thread_id).limit(1).stream()
    for msg in messages:
        updates["updated_at"] = datetime.utcnow().isoformat()
        messages_ref.document(msg.id).update(updates)
        return True
    return False

# Fetch messages by user (optional utility)
def get_messages_by_user(user_id, limit=20):
    query = messages_ref.where("user_id", "==", user_id).order_by("created_at", direction="DESCENDING").limit(limit)
    return [doc.to_dict() for doc in query.stream()]
