from app.db.firestore_helper import get_collection
from datetime import datetime
from google.cloud.firestore_v1 import FieldFilter

subscriptions_ref = get_collection("subscriptions")

def create_subscription(tier, price, level, duration_days):
    now = datetime.utcnow().isoformat()

    # Check for existing tier
    existing = subscriptions_ref.where(filter=FieldFilter("tier", "==", tier)).limit(1).stream()
    if any(existing):
        raise ValueError("Tier already exists")

    subscription_data = {
        "tier": tier,
        "price": price,
        "level": level,
        "duration_days": duration_days,
        "created_at": now,
        "updated_at": now
    }
    doc_ref = subscriptions_ref.document()
    subscription_data["plan_id"] = doc_ref.id
    doc_ref.set(subscription_data)
    return subscription_data

# Get subscription plan by id
def get_subscription_by_id(plan_id):
    doc = subscriptions_ref.document(plan_id).get()
    return doc.to_dict() if doc.exists else None

# Update a subscription plan
def update_subscription(plan_id, updates: dict):
    updates["updated_at"] = datetime.utcnow().isoformat()
    # Check for conflicting tier if updating tier
    if "tier" in updates:
        new_tier = updates["tier"]
        existing = subscriptions_ref.where(filter=FieldFilter("tier", "==", new_tier)).limit(1).stream()
        for doc in existing:
            if doc.id != plan_id:
                raise ValueError("Another subscription with this tier already exists")

    # Check for conflicting level if updating level
    if "level" in updates:
        new_level = updates["level"]
        existing_level = subscriptions_ref.where(filter=FieldFilter("level", "==", new_level)).limit(1).stream()
        for doc in existing_level:
            if doc.id != plan_id:
                raise ValueError("Another subscription with this level already exists")
    subscriptions_ref.document(plan_id).update(updates)

# Delete a subscription plan by plan_id
def delete_subscription(plan_id):
    subscriptions_ref.document(plan_id).delete()
    
# List all subscription plans
def list_subscriptions(limit=20, start_after=None):
    query = subscriptions_ref.order_by("created_at").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    return [doc.to_dict() for doc in query.stream()]

