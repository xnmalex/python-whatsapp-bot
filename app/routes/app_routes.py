from flask import Blueprint, request, jsonify
from app.db.app_dao import create_app, get_app_by_id, update_app, list_user_apps, delete_app
from app.db.subscription_dao import get_subscription_by_id
from app.utils.timestamp_utils import update_timestamp
from app.utils.subscription_utils import get_valid_user_plan  # centralized import
from google.cloud import firestore
import jwt
import os

app_blueprint = Blueprint("app", __name__, url_prefix="/api/v1/apps")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")

def get_user_id_from_token():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None


@app_blueprint.route("/create", methods=["POST"])
def create_new_app():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

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
def get_my_apps():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        apps = list_user_apps(user_id)
        return jsonify({"apps": apps}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve apps: {str(e)}"}), 500
    
@app_blueprint.route("/<app_id>", methods=["GET"])
def get_app_by_id_route(app_id):
    user_id = get_user_id_from_token()
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
def delete_app_route(app_id):
    user_id = get_user_id_from_token()
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
def update_app_settings(app_id):
    user_id = get_user_id_from_token()
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

