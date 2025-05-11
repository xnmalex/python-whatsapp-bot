from datetime import datetime, timezone
from app.db.firestore_helper import get_collection
from app.db.metrics_dao import increment_daily, increment_metric, get_summary_metrics
from google.cloud.firestore_v1 import FieldFilter

users_ref = get_collection("users")

# Create a new user
def create_user(email, password_hash, name, creator_id=None, role="user"):
    now = datetime.now(timezone.utc)
    user_data = {
        "email": email,
        "password": password_hash,
        "name": name,
        "role": role,
        "created_by": creator_id,
        "created_at": now,
        "updated_at": now
    }
    doc_ref = users_ref.document()
    user_data["user_id"] = doc_ref.id
    doc_ref.set(user_data)
    
    if role == "user":
        increment_metric("total_users")
        increment_daily("new_users")
    elif role == "admin":
        increment_metric("total_admin")
        increment_daily("new_admin")
    return user_data

# Get user by email
def get_user_by_email(email):
    users = users_ref.where(filter=FieldFilter("email", "==", email)).limit(1).stream()
    for user in users:
        return user.to_dict()
    return None

# Get user by ID
def get_user_by_id(user_id):
    doc = users_ref.document(user_id).get()
    return doc.to_dict() if doc.exists else None

# Update user fields
def update_user(user_id, updates: dict):
    updates["updated_at"] = datetime.now(timezone.utc)
    users_ref.document(user_id).update(updates)

# Delete user
def delete_user(user_id):
    users_ref.document(user_id).delete()

# List all users with pagination
def list_users(limit=10, start_after=None):
    query = users_ref.where(filter=FieldFilter("role", "==", "user")).order_by("created_at").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    
    users = query.stream()
    user_list = [user.to_dict() for user in users]
    
     # Fetch total user count from summary metrics
    summary = get_summary_metrics()
    total_users = summary.get("total_users", 0)
    return {
        "users": user_list,
        "total": total_users
    }

# List all admins with pagination
def list_admins(limit=10, start_after=None):
    query = users_ref.where(filter=FieldFilter("role", "==", "admin")).order_by("created_at").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    users = query.stream()
    admin_list = [user.to_dict() for user in users]

     # Fetch total user count from summary metrics
    summary = get_summary_metrics()
    total_admin = summary.get("total_admin", 0)

    return {
        "users": admin_list,
        "total": total_admin
    }