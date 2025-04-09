from app.db.firestore_helper import get_collection

subscriptions_ref = get_collection("subscriptions")

# Get subscription plan by tier
def get_subscription_by_tier(tier):
    doc = subscriptions_ref.document(tier).get()
    return doc.to_dict() if doc.exists else None

# Create or update a subscription plan
def set_subscription(tier, data):
    subscriptions_ref.document(tier).set(data)

# Delete a subscription plan by tier
def delete_subscription(tier):
    subscriptions_ref.document(tier).delete()

# List all subscription plans
def list_subscriptions():
    return [doc.to_dict() for doc in subscriptions_ref.stream()]

# Check if a level already exists in other tiers (excluding one)
def is_level_conflicting(level, exclude_tier=None):
    for doc in subscriptions_ref.stream():
        data = doc.to_dict()
        if doc.id != exclude_tier and data.get("level") == level:
            return True
    return False
