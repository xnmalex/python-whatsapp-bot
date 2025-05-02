from datetime import datetime
from google.cloud.firestore_v1 import FieldFilter
from app.db.firestore_helper import get_collection

contacts_ref = get_collection("contacts")

MAX_BATCH_WRITE = 500

def save_contact(user_id, platform, chat_id, name, phone_number=None, telegram_username=None):
    if not platform or not chat_id:
        raise ValueError("platform, and chat_id are required fields")
    now = datetime.utcnow().isoformat()
    contact_data = {
        "user_id":user_id,
        "platform": platform,
        "chat_id": chat_id,
        "name":name,
        "phone_number": phone_number,
        "telegram_username": telegram_username,
        "created_at": now,
        "updated_at": now
    }
    contacts_ref.document().set(contact_data)
    return contact_data

def save_contacts_batch(user_id, platform, contacts):
    from google.cloud import firestore
    client = firestore.Client()
    now = datetime.utcnow().isoformat()
    batches = [contacts[i:i + MAX_BATCH_WRITE] for i in range(0, len(contacts), MAX_BATCH_WRITE)]

    for batch_group in batches:
        batch = client.batch()
        for contact in batch_group:
            contact_data = {
                "user_id": user_id,
                "platform": platform,
                "chat_id": contact.get("chat_id"),
                "phone_number": contact.get("phone_number"),
                "telegram_username": contact.get("telegram_username"),
                "created_at": now,
                "updated_at": now
            }
            batch.set(contacts_ref.document(), contact_data)
        batch.commit()

def get_contact_by_id(user_id, platform, chat_id):
    query = contacts_ref.where(filter=FieldFilter("user_id", "==", user_id))\
                         .where(filter=FieldFilter("platform", "==", platform))\
                         .where(filter=FieldFilter("chat_id", "==", chat_id))\
                         .limit(1).stream()
    for doc in query:
        return doc.to_dict()
    return None

def list_contacts_by_app(user_id, limit=20, start_after=None):
    query = contacts_ref.where(filter=FieldFilter("user_id", "==", user_id)).order_by("created_at").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    return [doc.to_dict() for doc in query.stream()]

def list_contacts_by_platform(user_id, platform, limit=20, start_after=None):
    query = contacts_ref.where(filter=FieldFilter("user_id", "==", user_id))\
                         .where(filter=FieldFilter("platform", "==", platform))\
                         .order_by("created_at").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    return [doc.to_dict() for doc in query.stream()]

def update_contact(user_id, platform, chat_id, updates):
    query = contacts_ref.where(filter=FieldFilter("user_id", "==", user_id))\
                         .where(filter=FieldFilter("platform", "==", platform))\
                         .where(filter=FieldFilter("chat_id", "==", chat_id)).limit(1).stream()
    for doc in query:
        updates["updated_at"] = datetime.utcnow().isoformat()
        contacts_ref.document(doc.id).update(updates)
        return True
    return False

def delete_contact(user_id, platform, chat_id):
    query = contacts_ref.where(filter=FieldFilter("user_id", "==", user_id))\
                         .where(filter=FieldFilter("platform", "==", platform))\
                         .where(filter=FieldFilter("chat_id", "==", chat_id)).limit(1).stream()
    for doc in query:
        contacts_ref.document(doc.id).delete()
        return True
    return False