from datetime import datetime
import uuid
import secrets
from app.db.firestore_helper import get_collection
from google.cloud.firestore_v1 import FieldFilter

apps_ref = get_collection("apps")

# Create a new app
def create_app(owner_id, name):
    app_id = str(uuid.uuid4())
    app_token = secrets.token_hex(24)  # Secure token for webhook validation
    now = datetime.utcnow().isoformat()
    app_data = {
        "app_id": app_id,
        "owner_id": owner_id,
        "name": name,
        "openai_settings": {},
        "app_token": app_token,
        "waba_settings": {},
        "telegram_settings": {},
        "created_at": now,
        "updated_at": now
    }
    apps_ref.document(app_id).set(app_data)
    return app_data

# Get app by ID
def get_app_by_id(app_id):
    doc = apps_ref.document(app_id).get()
    return doc.to_dict() if doc.exists else None

# Get app by user ID (owner_id)
def get_app_by_user_id(user_id):
    query = apps_ref.where(filter=FieldFilter("owner_id", "==", user_id)).limit(1).stream()
    for doc in query:
        return doc.to_dict()
    return None

# Get app by app token
def get_app_by_app_token(app_token):
    query = apps_ref.where(filter=FieldFilter("app_token", "==", app_token)).limit(1).stream()
    for doc in query:
        return doc.to_dict()
    return None

# Get app by WABA phone number ID
def get_app_by_waba_phone_id(phone_number_id):
    query = apps_ref.where(filter=FieldFilter("waba_settings.phone_number_id", "==", phone_number_id)).limit(1).stream()
    for doc in query:
        return doc.to_dict()
    return None

# Update app fields
def update_app(app_id, updates: dict):
    updates["updated_at"] = datetime.utcnow().isoformat()
    apps_ref.document(app_id).update(updates)

# List all apps owned by a user
def list_user_apps(owner_id):
    apps = apps_ref.where(filter=FieldFilter("owner_id", "==", owner_id)).stream()
    return [app.to_dict() for app in apps]

# Delete app by ID
def delete_app(app_id):
    apps_ref.document(app_id).delete()
