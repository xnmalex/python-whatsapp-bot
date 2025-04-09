from datetime import datetime
import uuid
from app.db.firestore_helper import get_collection

users_ref = get_collection("users")

# Create a new user
def create_user(email, password_hash, name, role="user"):
    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    user_data = {
        "user_id": user_id,
        "email": email,
        "password": password_hash,
        "name": name,
        "role": role,
        "created_at": now,
        "updated_at": now
    }
    users_ref.document(user_id).set(user_data)
    return user_data

# Get user by email
def get_user_by_email(email):
    users = users_ref.where("email", "==", email).limit(1).stream()
    for user in users:
        return user.to_dict()
    return None

# Get user by ID
def get_user_by_id(user_id):
    doc = users_ref.document(user_id).get()
    return doc.to_dict() if doc.exists else None

# Update user fields
def update_user(user_id, updates: dict):
    updates["updated_at"] = datetime.utcnow().isoformat()
    users_ref.document(user_id).update(updates)

# Delete user
def delete_user(user_id):
    users_ref.document(user_id).delete()

# List all users with pagination
def list_users(limit=10, start_after=None):
    query = users_ref.order_by("created_at").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    users = query.stream()
    return [user.to_dict() for user in users]