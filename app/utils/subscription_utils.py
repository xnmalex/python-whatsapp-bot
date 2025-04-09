from app.db.user_subscription_dao import get_user_subscription, delete_user_subscription, is_subscription_expired
from app.db.subscription_dao import get_subscription_by_tier


def get_valid_user_plan(user_id):
    user_sub = get_user_subscription(user_id)
    tier = "free"
    level = 0

    if user_sub:
        tier = user_sub.get("tier", "free")
        expiry_at = user_sub.get("expiry_at")
        level = user_sub.get("level", 0)

        if is_subscription_expired(expiry_at):
            print(f"Subscription expired for user {user_id}. Falling back to free tier.")
            delete_user_subscription(user_id)
            return "free", 0

        if tier != "free" and not get_subscription_by_tier(tier):
            print(f"Tier '{tier}' no longer exists. Falling back to free tier for user {user_id}.")
            delete_user_subscription(user_id)
            return "free", 0

    return tier, level