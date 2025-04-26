from datetime import datetime
from app.db.firestore_helper import get_collection
from google.cloud.firestore_v1 import FieldFilter
from google.cloud import firestore

contacts_ref = get_collection("contacts")

MAX_BATCH_WRITE = 500  # Firestore batch limit

def save_contact(app_id, platform, chat_id, phone_number=None, telegram_username=None):
    now = datetime.utcnow().isoformat()
    contact_data = {
        "app_id": app_id,
        "platform": platform,
        "chat_id": chat_id,
        "phone_number": phone_number,
        "telegram_username": telegram_username,
        "updated_at": now,
        "created_at": now
    }
    doc_ref = contacts_ref.document()  # auto-generate ID
    doc_ref.set(contact_data)
    return contact_data

def save_contacts_batch(app_id, platform, contacts):
    """
    contacts: list of dicts with keys: chat_id, phone_number, telegram_username
    """
    batches = [contacts[i:i + MAX_BATCH_WRITE] for i in range(0, len(contacts), MAX_BATCH_WRITE)]
    client = firestore.Client()
    now = datetime.utcnow().isoformat()

    for batch_group in batches:
        batch = client.batch()
        for contact in batch_group:
            chat_id = contact["chat_id"]
            contact_data = {
                "app_id": app_id,
                "platform": platform,
                "chat_id": chat_id,
                "phone_number": contact.get("phone_number"),
                "telegram_username": contact.get("telegram_username"),
                "updated_at": now,
                "created_at": now
            }
            doc_ref = contacts_ref.document()  # auto-generate ID
            batch.set(doc_ref, contact_data)
        batch.commit()

def get_contact_by_id(app_id, platform, chat_id):
    query = contacts_ref.where(filter=FieldFilter("app_id", "==", app_id))\
                         .where(filter=FieldFilter("platform", "==", platform))\
                         .where(filter=FieldFilter("chat_id", "==", chat_id))\
                         .limit(1).stream()
    for doc in query:
        return doc.to_dict()
    return None

def list_contacts_by_app(app_id):
    query = contacts_ref.where(filter=FieldFilter("app_id", "==", app_id)).stream()
    return [doc.to_dict() for doc in query]

def update_contact(app_id, platform, chat_id, updates):
    query = contacts_ref.where(filter=FieldFilter("app_id", "==", app_id))\
                         .where(filter=FieldFilter("platform", "==", platform))\
                         .where(filter=FieldFilter("chat_id", "==", chat_id))\
                         .limit(1).stream()
    for doc in query:
        updates["updated_at"] = datetime.utcnow().isoformat()
        contacts_ref.document(doc.id).update(updates)
        break

def delete_contact(app_id, platform, chat_id):
    query = contacts_ref.where(filter=FieldFilter("app_id", "==", app_id))\
                         .where(filter=FieldFilter("platform", "==", platform))\
                         .where(filter=FieldFilter("chat_id", "==", chat_id))\
                         .limit(1).stream()
    for doc in query:
        contacts_ref.document(doc.id).delete()
        break
