from flask import Blueprint, request, jsonify
from app.db.user_dao import list_users
from app.db.user_subscription_dao import get_user_subscription, delete_user_subscription, set_user_subscription
from app.decorators.auth_decorators import admin_required
import jwt
import os

admin_user_blueprint = Blueprint("admin_user", __name__)
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")

def is_admin():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("role") == "admin"
    except Exception:
        return False

@admin_user_blueprint.route("/api/v1/admin/users", methods=["GET"])
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


@admin_user_blueprint.route("/api/v1/admin/subscriptions/terminate/<user_id>", methods=["DELETE"])
@admin_required
def terminate_user_subscription(user_id):
    try:
        delete_user_subscription(user_id)
        return jsonify({"success": True, "message": f"Subscription for user {user_id} terminated."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    

@admin_user_blueprint.route("/api/v1/admin/subscriptions/add", methods=["POST"])
@admin_required
def add_user_subscription():
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