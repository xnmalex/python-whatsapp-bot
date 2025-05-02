from flask import Blueprint, request, jsonify, g
from app.db.app_dao import create_app, get_app_by_id, update_app, list_user_apps, delete_app
from app.db.subscription_dao import get_subscription_by_id
from app.utils.timestamp_utils import update_timestamp
from app.utils.subscription_utils import get_valid_user_plan  # centralized import
from app.decorators.auth_decorators import user_required
from google.cloud import firestore
from datetime import datetime

app_blueprint = Blueprint("app", __name__, url_prefix="/api/v1/apps")


@app_blueprint.route("/create", methods=["POST"])
@user_required
def create_new_app():
    user_id = g.current_user["user_id"]
    data = request.get_json()
    name = data.get("name")

    if not name:
        return jsonify({"error": "'name' is required."}), 400

    try:
        plan_id = get_valid_user_plan(user_id)
        if plan_id:
            plan = get_subscription_by_id(plan_id)
            max_apps = plan.get("max_apps", 1) if plan else 1
        else:
            max_apps =1

        existing_apps = list_user_apps(user_id)
        if len(existing_apps) >= max_apps:
            return jsonify({"error": f"Your subscription allows a maximum of {max_apps} app(s)."}), 403

        app_data = create_app(owner_id=user_id, name=name)

        return jsonify({"message": "App created successfully.", "app": app_data}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create app: {str(e)}"}), 500

@app_blueprint.route("", methods=["GET"])
@user_required
def get_my_apps():
    user_id = g.current_user["user_id"]
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        apps = list_user_apps(user_id)
        return jsonify({"apps": apps}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve apps: {str(e)}"}), 500
    
@app_blueprint.route("/<app_id>", methods=["GET"])
@user_required
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

        if "openai_settings" in data:
            settings = data["openai_settings"]
            if not settings:
                updates["openai_settings"] = firestore.DELETE_FIELD
            elif not settings.get("assistant_id") or not settings.get("openai_api_key"):
                return jsonify({"error": "Missing assistant_id or openai_api_key in openai_settings"}), 400
            else:
                updates["openai_settings"] = settings

        if "waba_settings" in data:
            settings = data["waba_settings"]
            if not settings:
                updates["waba_settings"] = firestore.DELETE_FIELD
            elif not isinstance(settings, list):
                return jsonify({"error": "waba_settings must be a list"}), 400
            else:
                for s in settings:
                    if not s.get("phone_number_id") or not s.get("waba_token"):
                        return jsonify({"error": "Each WABA setting must include phone_number_id and waba_token"}), 400
                updates["waba_settings"] = settings

        if "telegram_settings" in data:
            settings = data["telegram_settings"]
            if not settings:
                updates["telegram_settings"] = firestore.DELETE_FIELD
            elif not isinstance(settings, list):
                return jsonify({"error": "telegram_settings must be a list"}), 400
            else:
                for s in settings:
                    if not s.get("bot_token"):
                        return jsonify({"error": "Each Telegram setting must include bot_token"}), 400
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