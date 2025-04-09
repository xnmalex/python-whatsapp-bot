from datetime import datetime
import uuid
from app.db.firestore_helper import get_collection

apps_ref = get_collection("apps")

# Create a new app
def create_app(owner_id, name):
    app_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    app_data = {
        "app_id": app_id,
        "owner_id": owner_id,
        "name": name,
        "openai_settings": {},
        "waba_settings": {},
        "created_at": now,
        "updated_at": now
    }
    apps_ref.document(app_id).set(app_data)
    return app_data

# Get app by ID
def get_app_by_id(app_id):
    doc = apps_ref.document(app_id).get()
    return doc.to_dict() if doc.exists else None

# Update app fields
def update_app(app_id, updates: dict):
    updates["updated_at"] = datetime.utcnow().isoformat()
    apps_ref.document(app_id).update(updates)

# List all apps owned by a user
def list_user_apps(owner_id):
    apps = apps_ref.where("owner_id", "==", owner_id).stream()
    return [app.to_dict() for app in apps]

# Delete app by ID
def delete_app(app_id):
    apps_ref.document(app_id).delete()
