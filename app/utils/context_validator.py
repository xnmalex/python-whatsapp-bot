from app.db.app_dao import get_app_by_user_id
from app.db.user_subscription_dao import get_user_subscription

def validate_user_and_subscription(user_id: str):
    app = get_app_by_user_id(user_id)
    if not app:
        raise ValueError("No app found for this user.")

    app_id = app.get("app_id")
    subscription = get_user_subscription(user_id)

    if not subscription:
        raise ValueError("No subscription found for this user.")

    return {
        "user_id": user_id,
        "app_id": app_id,
        "subscription": subscription
    }
