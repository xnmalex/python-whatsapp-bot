from datetime import datetime
from app.db.firestore_helper import get_collection
from google.cloud.firestore_v1 import FieldFilter
from app.db.metrics_dao import increment_metric, decrement_metric
from app.db.subscription_dao import get_subscription_by_id

user_subscriptions_ref = get_collection("user_subscriptions")

# Create or update a user subscription
def set_user_subscription(user_id, plan_id):
    now = datetime.utcnow().isoformat()
    
    plan_data = get_subscription_by_id(plan_id)
    if not plan_data:
        raise ValueError("Invalid plan_id")
    plan_data["updated_at"] = now
   
    user_subscriptions_ref.document(user_id).set(plan_data)
    if plan_data["tier"] != "free":
        increment_metric("total_paid_subscriptions")
    return plan_data

# Get user subscription by user ID
def get_user_subscription(user_id):
    doc = user_subscriptions_ref.document(user_id).get()
    return doc.to_dict() if doc.exists else None

# Delete user subscription
def delete_user_subscription(user_id):
    query = user_subscriptions_ref.where(filter=FieldFilter("user_id", "==", user_id)).limit(1).stream()
    for doc in query:
        data = doc.to_dict()
        if data["tier"] != "free":
            decrement_metric("total_paid_subscriptions")
        user_subscriptions_ref.document(doc.id).delete()
        return True
    return False

# Check if subscription is expired
def is_subscription_expired(expiry_at):
    if not expiry_at:
        return False
    try:
        return datetime.utcnow() > datetime.fromisoformat(expiry_at)
    except Exception as e:
        print(f"[user_subscription_dao] Error parsing expiry_at: {e}")
        return True

# List all user subscriptions (optional utility)
def list_user_subscriptions(limit=10, start_after=None):
    query = user_subscriptions_ref.order_by("created_at").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    subs = query.stream()
    return [sub.to_dict() for sub in subs]
