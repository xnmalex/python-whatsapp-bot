from datetime import datetime, timezone
import uuid
import secrets
from app.db.firestore_helper import get_collection
from app.db.metrics_dao import increment_daily, decrement_daily, increment_metric, decrement_metric
from google.cloud.firestore_v1 import FieldFilter, Query

apps_ref = get_collection("apps")

def is_valid_settings(settings: dict):
    """Helper to validate settings safely."""
    if not isinstance(settings, dict):
        return False
    if not settings:
        return False
    return any(v for v in settings.values() if v not in ("", None, {}, []))

# Create a new app
def create_app(owner_id, owner_name, name, settings=None):
    app_id = str(uuid.uuid4())
    app_token = secrets.token_hex(24)  # Secure token for webhook validation
    now = datetime.now(timezone.utc)
    
    # Initialize app data
    app_data = {
        "app_id": app_id,
        "owner_id": owner_id,
        "owner_name": owner_name,
        "name": name,
        "app_token": app_token,
        "created_at": now,
        "updated_at": now
    }
    
    # Optional: parse incoming settings
    settings = settings or {}
    # Validate and assign bot type
    bot_type = settings.get("bot")
    if bot_type not in [None, "whatsapp", "telegram"]:
        raise ValueError("Invalid bot type. Must be 'whatsapp' or 'telegram'")
    if bot_type:
        app_data["bot"] = bot_type

    # OpenAI settings
    if "openai_settings" in settings:
        openai = settings["openai_settings"]
        if not isinstance(openai, dict):
            raise ValueError("openai_settings must be an object")
        if openai and (not openai.get("assistant_id") or not openai.get("openai_api_key")):
            raise ValueError("Missing assistant_id or openai_api_key in openai_settings")
        app_data["openai_settings"] = openai
    else:
        app_data["openai_settings"] = {}

    # WhatsApp settings (only if bot == whatsapp)
    if "waba_settings" in settings:
        if bot_type != "whatsapp":
            raise ValueError("waba_settings is only allowed when bot is 'whatsapp'")
        waba = settings["waba_settings"]
        if not isinstance(waba, dict):
            raise ValueError("waba_settings must be an object")
        if not waba.get("phone_number_id") or not waba.get("waba_token"):
            raise ValueError("Missing phone_number_id or waba_token in waba_settings")
        app_data["waba_settings"] = waba

    # Telegram settings (only if bot == telegram)
    if "telegram_settings" in settings:
        if bot_type != "telegram":
            raise ValueError("telegram_settings is only allowed when bot is 'telegram'")
        telegram = settings["telegram_settings"]
        if not isinstance(telegram, dict):
            raise ValueError("telegram_settings must be an object")
        if not telegram.get("bot_token"):
            raise ValueError("Missing bot_token in telegram_settings")
        app_data["telegram_settings"] = telegram
        
    apps_ref.document(app_id).set(app_data)
    increment_metric("total_apps")
    increment_daily("apps_created")
    return app_data

# Get app by ID
def get_app_by_id(app_id):
    doc = apps_ref.document(app_id).get()
    return doc.to_dict() if doc.exists else None

# Get app by user ID (owner_id)
def get_app_by_user_id(user_id, limit=20, start_after_created_at=None, sort_order="asc", platform=None):
    direction = Query.ASCENDING if sort_order == "asc" else Query.DESCENDING

    query = apps_ref.where(filter=FieldFilter("owner_id", "==", user_id)).order_by("created_at", direction=direction)
    
    if platform in ["whatsapp", "telegram"]:
        query = query.where("bot", "==", platform)

    # Handle pagination with start_after
    if start_after_created_at:
        try:
            query = query.start_after({"created_at": start_after_created_at})
        except Exception:
            raise ValueError("Invalid start_after_created_at timestamp. Use ISO format.")

    query = query.limit(limit).stream()
    return [doc.to_dict() for doc in query]

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
    updates["updated_at"] = datetime.now(timezone.utc)
    app_doc = apps_ref.document(app_id).get()
    if not app_doc.exists:
        return None

    existing_data = app_doc.to_dict()

    # Check for WABA settings change
    if "waba_settings" in updates:
        old = existing_data.get("waba_settings") or {}
        new = updates["waba_settings"] or {}
        was_set = is_valid_settings(old)
        now_set = is_valid_settings(new)
        if not was_set and now_set:
            increment_metric("total_whatsapp_bots")
            increment_daily("new_whatsapp_bots")
        elif was_set and not now_set:
            decrement_metric("total_whatsapp_bots")
            decrement_daily("new_whatsapp_bots")

    # Check for Telegram settings change
    if "telegram_settings" in updates:
        old = existing_data.get("telegram_settings") or {}
        new = updates["telegram_settings"] or {}
        was_set = is_valid_settings(old)
        now_set = is_valid_settings(new)
        if not was_set and now_set:
            increment_metric("total_telegram_bots")
            increment_daily("new_telegram_bots")
        elif was_set and not now_set:
            decrement_metric("total_telegram_bots")
            decrement_daily("new_telegram_bots")
            
    apps_ref.document(app_id).update(updates)

# List all apps owned by a user
def list_user_apps(owner_id, limit=20, start_after_created_at=None, sort_order="asc", platform=None):
    query = apps_ref.where(filter=FieldFilter("owner_id", "==", owner_id))
    if platform in ["whatsapp", "telegram"]:
        query = query.where("bot", "==", platform)

    # Handle pagination with start_after
    if start_after_created_at:
        try:
            query = query.start_after({"created_at": start_after_created_at})
        except Exception:
            raise ValueError("Invalid start_after_created_at timestamp. Use ISO format.")

    query = query.limit(limit).stream()
    return [doc.to_dict() for doc in query]

# List all apps (admin access)
def list_all_apps(limit=20, start_after=None):
    query = apps_ref.order_by("created_at").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    return [doc.to_dict() for doc in query.stream()]

# Delete app by ID
def delete_app(app_id):
    app_doc = apps_ref.document(app_id).get()
    if app_doc.exists:
        data = app_doc.to_dict()
        if data.get("waba_settings"):
            decrement_metric("total_whatsapp_bots")
            increment_daily("new_whatsapp_bots")
        if data.get("telegram_settings"):
            decrement_metric("total_telegram_bots")
            decrement_daily("new_telegram_bots")
        decrement_metric("total_apps")
    apps_ref.document(app_id).delete()


def fetch_all_apps_with_filters(limit=20, start_after_raw=None, sort_order="asc", platform=None):
    direction = Query.ASCENDING if sort_order == "asc" else Query.DESCENDING
    query = apps_ref.order_by("created_at", direction=direction)

    # Filter by bot platform if specified
    if platform in ["whatsapp", "telegram"]:
        query = query.where("bot", "==", platform)

    # Handle pagination
    if start_after_raw:
        try:
            start_after_ts = datetime.fromisoformat(start_after_raw)
            query = query.start_after({"created_at": start_after_ts})
        except Exception:
            raise ValueError("Invalid start_after timestamp format. Use ISO format.")

    query = query.limit(limit)
    docs = query.stream()

    result = []
    for doc in docs:
        app = doc.to_dict()
        app["id"] = doc.id

        # Normalize for frontend consistency
        app["waba_settings"] = app.get("waba_settings") if isinstance(app.get("waba_settings"), dict) else None
        app["telegram_settings"] = app.get("telegram_settings") if isinstance(app.get("telegram_settings"), dict) else None

        result.append(app)

    return result