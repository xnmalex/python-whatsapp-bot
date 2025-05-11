from flask import Blueprint, request, jsonify, g
from app.db.app_dao import create_app, get_app_by_id, update_app, list_user_apps, delete_app, get_app_by_user_id
from app.db.subscription_dao import get_subscription_by_id
from app.db.user_dao import get_user_by_id
from app.utils.timestamp_utils import update_timestamp
from app.utils.subscription_utils import get_valid_user_plan  # centralized import
from app.decorators.auth_decorators import user_required, auth_required
from google.cloud import firestore
from datetime import datetime
import traceback

app_blueprint = Blueprint("app", __name__, url_prefix="/api/v1/apps")


@app_blueprint.route("/create", methods=["POST"])
@auth_required
def create_new_app():
    role = g.current_user["role"]
    
    owner_name = g.current_user.get("name")  # Get owner's name
    data = request.get_json()
    name = data.get("name")
    settings = data.get("settings")
    user_id = g.current_user["user_id"] 
    
    if role == "super_admin":
        return jsonify({"error": "super admin not allowed to create new bot"}), 400
     
    if role == "admin":
        if not data.get("user_id"):
            return jsonify({"error": "Admin must provide user_id to create app on behalf"}), 400
        user_id = data.get("user_id")
        user = get_user_by_id(user_id)
        owner_name = user["name"]
        
    # fallback if role is not admin or super_admin
    if not user_id:
        return jsonify({"error": "User ID is missing"}), 400

    if not name:
        return jsonify({"error": "'name' is required."}), 400

    try:
        # plan_id = get_valid_user_plan(user_id)
        # if plan_id:
        #     plan = get_subscription_by_id(plan_id)
        #     max_apps = plan.get("max_apps", 1) if plan else 1
        # else:
        #     max_apps =1

        # existing_apps = list_user_apps(user_id)
        # if len(existing_apps) >= max_apps:
        #     return jsonify({"error": f"Your subscription allows a maximum of {max_apps} app(s)."}), 403

        app_data = create_app(owner_id=user_id, owner_name=owner_name, name=name, settings=settings)

        return jsonify({"message": "App created successfully.", "app": app_data}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to create app: {str(e)}"}), 500

@app_blueprint.route("", methods=["GET"])
@user_required
def get_my_apps():
    user_id = g.current_user["user_id"]
   
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        platform = request.args.get("platform")
        if platform not in ["whatsapp", "telegram"]:
            return jsonify({"error": "Invalid or missing platform. Must be 'whatsapp' or 'telegram'"}), 400
        apps = list_user_apps(user_id, platform=platform)
        return jsonify({"apps": apps}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve apps: {str(e)}"}), 500
    
@app_blueprint.route("/<app_id>", methods=["GET"])
@auth_required
def get_app_by_id_route(app_id):
    user_id = g.current_user["user_id"]
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        app = get_app_by_id(app_id)
        if not app:
            return jsonify({"error": "App not found."}), 404
        if app.get("owner_id") != user_id:
            return jsonify({"error": "Forbidden"}), 403
        return jsonify({"app": app}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch app: {str(e)}"}), 500

@app_blueprint.route("/<app_id>", methods=["DELETE"])
@user_required
def delete_app_route(app_id):
    user_id = g.current_user["user_id"]
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        app_data = get_app_by_id(app_id)
        if not app_data:
            return jsonify({"error": "App not found"}), 404
        if app_data.get("owner_id") != user_id:
            return jsonify({"error": "Forbidden"}), 403

        delete_app(app_id)
        return jsonify({"message": "App deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete app: {str(e)}"}), 500

@app_blueprint.route("/<app_id>/settings", methods=["PATCH"])
@user_required
def update_app_settings(app_id):
    user_id = g.current_user["user_id"]
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    try:
        app_data = get_app_by_id(app_id)
        if not app_data:
            return jsonify({"error": "App not found"}), 404
        if app_data.get("owner_id") != user_id:
            return jsonify({"error": "Forbidden"}), 403

        updates = {}

        # Enforce bot type
        bot_type = data.get("bot")
        if bot_type not in ["whatsapp", "telegram"]:
            return jsonify({"error": "Invalid or missing bot type. Must be 'whatsapp' or 'telegram'"}), 400
        updates["bot"] = bot_type

        # OpenAI settings
        if "openai_settings" in data:
            settings = data["openai_settings"]
            if not settings:
                updates["openai_settings"] = firestore.DELETE_FIELD
            elif not settings.get("assistant_id") or not settings.get("openai_api_key"):
                return jsonify({"error": "Missing assistant_id or openai_api_key in openai_settings"}), 400
            else:
                updates["openai_settings"] = settings

        # WABA settings (must be a single object if bot is whatsapp)
        if "waba_settings" in data:
            if bot_type != "whatsapp":
                return jsonify({"error": "waba_settings is only allowed when bot is 'whatsapp'"}), 400

            settings = data["waba_settings"]
            if not settings:
                updates["waba_settings"] = firestore.DELETE_FIELD
            elif not isinstance(settings, dict):
                return jsonify({"error": "waba_settings must be an object"}), 400
            elif not settings.get("phone_number_id") or not settings.get("waba_token"):
                return jsonify({"error": "waba_settings must include phone_number_id and waba_token"}), 400
            else:
                updates["waba_settings"] = settings

        # Telegram settings (must be a single object if bot is telegram)
        if "telegram_settings" in data:
            if bot_type != "telegram":
                return jsonify({"error": "telegram_settings is only allowed when bot is 'telegram'"}), 400

            settings = data["telegram_settings"]
            if not settings:
                updates["telegram_settings"] = firestore.DELETE_FIELD
            elif not isinstance(settings, dict):
                return jsonify({"error": "telegram_settings must be an object"}), 400
            elif not settings.get("bot_token"):
                return jsonify({"error": "telegram_settings must include bot_token"}), 400
            else:
                updates["telegram_settings"] = settings

        if not updates:
            return jsonify({"error": "No valid settings to update"}), 400

        updates.update(update_timestamp())
        update_app(app_id, updates)

        return jsonify({"message": "App settings updated successfully"}), 200
       
    except Exception as e:
        return jsonify({"error": f"Failed to update settings: {str(e)}"}), 500

@app_blueprint.route("/<app_id>/autoreply", methods=["PATCH"])
@user_required
def update_auto_reply_setting(app_id):
    try:
        data = request.get_json()
        user_id = g.current_user["user_id"]
        mode = data.get("mode")  # should be 'off', 'auto', or 'scheduled'
        schedule = data.get("schedule")  # ISO 8601 string if mode is scheduled

        if mode not in ["off", "auto", "scheduled"]:
            return jsonify({"success": False, "message": "Mode must be one of 'off', 'auto', or 'scheduled'"}), 400

        if mode == "scheduled":
            if not isinstance(schedule, dict):
                return jsonify({"success": False, "message": "schedule must be a dictionary with weekdays and time ranges"}), 400

            valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
            for day, time_range in schedule.items():
                if day.lower() not in valid_days:
                    return jsonify({"success": False, "message": f"Invalid weekday: {day}"}), 400
                if not isinstance(time_range, dict) or "start" not in time_range or "end" not in time_range:
                    return jsonify({"success": False, "message": f"Invalid time range for {day}. Must include 'start' and 'end'"}), 400
       
        app_data = get_app_by_id(app_id)
        if not app_data:
            return jsonify({"error": "App not found"}), 404

        if app_data.get("owner_id") != user_id:
            return jsonify({"error": "Forbidden"}), 403

        update_fields = {
            "ai_reply_mode": mode,
            **update_timestamp()
        }
        
        if mode == "scheduled":
            update_fields["scheduled_schedule"] = schedule

        update_app(app_id, update_fields)

        return jsonify({"success": True, "message": f"AI reply mode set to {mode} for app {app_id}."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
    
@app_blueprint.route("/user-bots", methods=["GET"])
@auth_required
def get_user_bots():
    try:
        role = g.current_user["role"]
        requested_user_id = request.args.get("user_id")
        if role in ["admin", "super_admin"]:
            user_id = requested_user_id
        else:
            user_id = g.current_user["user_id"]

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        platform_filter = request.args.get("platform")  # 'whatsapp', 'telegram', or None
        start_after = request.args.get("start_after_created_at")
        sort_order = request.args.get("sort_order", "asc")
        limit = int(request.args.get("limit", 20))

        apps = get_app_by_user_id(
            user_id=user_id,
            limit=limit,
            start_after_created_at=start_after,
            sort_order=sort_order
        )

        whatsapp_bots = []
        telegram_bots = []
        last_created_at = None

        for app in apps:
            app_id = app.get("app_id")
            base_data = {
                "app_id": app_id,
                "app_name": app.get("name"),
                "owner_id": app.get("owner_id"),
                "owner_name": app.get("owner_name", "Unknown"),
                "openai_settings": app.get("openai_settings", {}),
                "created_at": app.get("created_at")
            }
            
            if base_data["created_at"]:
                last_created_at = base_data["created_at"]

            if isinstance(app.get("waba_settings"), dict):
                whatsapp_bots.append({**base_data, **app["waba_settings"]})

            if isinstance(app.get("telegram_settings"), dict):
                telegram_bots.append({**base_data, **app["telegram_settings"]})

        # Return based on platform filter
        if platform_filter == "whatsapp":
            return jsonify({
                "bots": whatsapp_bots,
                "count": len(whatsapp_bots),
                "platform": "whatsapp",
                "last_created_at": last_created_at
            }), 200

        elif platform_filter == "telegram":
            return jsonify({
                "bots": telegram_bots,
                "count": len(telegram_bots),
                "platform": "telegram",
                "last_created_at": last_created_at
            }), 200

        # Default: all bots
        return jsonify({
            "whatsapp_bots": whatsapp_bots,
            "telegram_bots": telegram_bots,
            "count": len(whatsapp_bots) + len(telegram_bots),
            "last_created_at": last_created_at,
            "platform": "all"
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500