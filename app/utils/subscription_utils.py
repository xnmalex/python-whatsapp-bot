from app.db.user_subscription_dao import get_user_subscription, delete_user_subscription, is_subscription_expired
from app.db.subscription_dao import get_subscription_by_id


def get_valid_user_plan(user_id):
    user_sub = get_user_subscription(user_id)
    tier = "free"

    if user_sub:
        plan_id = user_sub.get("plan_id")
        tier = user_sub.get("tier", "free")
        expiry_at = user_sub.get("expiry_at")

        if is_subscription_expired(expiry_at):
            print(f"Subscription expired for user {user_id}. Falling back to free tier.")
            delete_user_subscription(user_id)
            return None

        if tier != "free" and not get_subscription_by_id(plan_id):
            print(f"Tier '{tier}' no longer exists. Falling back to free tier for user {user_id}.")
            delete_user_subscription(user_id)
            return None

    return plan_id