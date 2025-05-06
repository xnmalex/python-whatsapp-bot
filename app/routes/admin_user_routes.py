from flask import Blueprint, request, jsonify
from app.db.user_dao import list_users, get_user_by_email, update_user
from app.db.user_subscription_dao import get_user_subscription, delete_user_subscription, set_user_subscription
from app.decorators.auth_decorators import admin_required
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

        users = list_users(limit=limit, start_after=start_after)
        user_list = []

        for user in users:
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

        return jsonify({"success": True, "users": user_list}), 200
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