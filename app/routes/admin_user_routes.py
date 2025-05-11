from flask import Blueprint, request,g, jsonify
from app.db.user_dao import list_users, get_user_by_email, update_user, get_user_by_id
from app.db.app_dao import list_all_apps
from app.db.user_subscription_dao import get_user_subscription, delete_user_subscription, set_user_subscription
from app.decorators.auth_decorators import admin_auth_required
from app.utils.password_utils import hash_password
from app.db.token_blacklist import blacklist_all_tokens_for_user
import logging
import jwt
import os

admin_user_blueprint = Blueprint("admin_user", __name__, url_prefix="/api/v1/admin")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")

def is_admin():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("role") == "admin" or payload.get("role") == "super_admin"
    except Exception:
        return False

@admin_user_blueprint.route("/users", methods=["GET"])
def list_users_with_subscriptions():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        limit = int(request.args.get("limit", 20))
        start_after = request.args.get("start_after", None)

        data = list_users(limit=limit, start_after=start_after)
        user_list = []

        for user in data.get("users", []):
            subscription = get_user_subscription(user.get("user_id"))
            user_info = {
                "user_id": user.get("user_id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "role": user.get("role"),
                "created_at": user.get("created_at"),
                "subscription": subscription
            }
            user_list.append(user_info)

        return jsonify({"success": True, "users": user_list, "total":data.get("total", 0)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@admin_user_blueprint.route("/apps", methods=["GET"])
def list_all_user_apps():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        limit = int(request.args.get("limit", 20))
        start_after = request.args.get("start_after", None)

        apps = list_all_apps(limit=limit, start_after=start_after)
        apps_list = []
        for user in apps:
        
            app_info = {
                "name": user.get("name"),
                "owner_id": user.get("owner_id"),
                "openai_settings": user.get("name"),
                "telegram_settings": user.get("telegram_settings"),
                "waba_settings": user.get("waba_settings"),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at"),
            }
            apps_list.append(app_info)
        return jsonify({"success": True, "apps": apps_list}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@admin_user_blueprint.route("/subscriptions/terminate/<user_id>", methods=["DELETE"])
def terminate_user_subscription(user_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        delete_user_subscription(user_id)
        return jsonify({"success": True, "message": f"Subscription for user {user_id} terminated."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@admin_user_blueprint.route("/subscriptions/add", methods=["POST"])
def add_user_subscription():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        plan_id = data.get("plan_id")

        if not user_id or not plan_id:
            return jsonify({"success": False, "message": "user_id and plan_id are required"}), 400

        set_user_subscription(user_id, plan_id)
        return jsonify({"success": True, "message": f"Subscription for user {user_id} added with plan {plan_id}."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@admin_user_blueprint.route("/reset-user-password", methods=["POST"])
def admin_reset_user_password():
    #only super admin and admin can reset user password
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    email = data.get("email")
    new_password = data.get("new_password")

    if not email or not new_password:
        return jsonify({"success": False, "message": "Missing email or new password"}), 400

    user = get_user_by_email(email)
    if not user or user.get("role") != "user":
        return jsonify({"success": False, "message": "Target must be a regular user"}), 403

    update_user(user["user_id"], {"password": hash_password(new_password)})
    blacklist_all_tokens_for_user(user["user_id"])
    
    logging.info(f"[Admin] Reset password for {email}")
    return jsonify({"success": True, "message": f"Password reset for user {email}"}), 200


@admin_user_blueprint.route("/update_user_email", methods=["POST"])
@admin_auth_required
def admin_update_email():
    # Only super admin and admin can update user email
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = request.get_json()
        new_email = data.get("email")
        user_id = data.get("user_id")

        if not new_email or not user_id:
            return jsonify({"success": False, "message": "Missing user_id or new email"}), 400

        user = get_user_by_id(user_id)
        if not user or user.get("role") != "user":
            return jsonify({"success": False, "message": "Target must be a regular user"}), 403

        # Optional: Check if email already exists
        if get_user_by_email(new_email):
            return jsonify({"success": False, "message": "Email already in use"}), 409

        # Get current admin info
        admin_id =  g.current_user["user_id"]
        admin_name = g.current_user["name"]

        # Update email and track who updated it
        update_user(user_id, {
            "email": new_email,
            "updated_by": {
                "admin_id": admin_id,
                "admin_name": admin_name
            }
        })

        logging.info(f"[Admin] {admin_name} ({admin_id}) updated email for user_id {user_id} to {new_email}")
        return jsonify({
            "success": True,
            "message": f"Email updated to {new_email} by admin {admin_name}"
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500