from flask import Blueprint, request, jsonify
import os
import jwt
from app.db import user_subscription_dao, subscription_dao

user_subscription_bp = Blueprint("user_subscription", __name__, url_prefix="/api/v1/subscriptions")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")

def get_user_id():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None

@user_subscription_bp.route("/subscribe", methods=["POST"])
def subscribe_to_plan():
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    plan_id = data.get("plan_id")

    if not plan_id:
        return jsonify({"error": "plan id is required."}), 400

    try:
        plan_data = subscription_dao.get_subscription_by_id(plan_id)
        if not plan_data:
            return jsonify({"error": "Subscription plan not found."}), 404

        level = plan_data.get("level", 0)
        tier = plan_data.get("tier")       

        current_sub = user_subscription_dao.get_user_subscription(user_id)
        if current_sub:
            current_level = current_sub.get("level", 0)
            if level < current_level:
                return jsonify({"error": f"You cannot downgrade from a higher tier to '{tier}'."}), 403
            if current_sub.get("tier") == tier:
                return jsonify({"message": f"You are already subscribed to '{tier}'."}), 200

        user_subscription_dao.set_user_subscription(user_id, plan_id)

        return jsonify({"message": f"Subscribed to '{tier}' successfully."}), 200
    except Exception as e:
        return jsonify({"error": f"Subscription failed: {str(e)}"}), 500


@user_subscription_bp.route("/me", methods=["GET"])
def get_my_subscription():
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        sub = user_subscription_dao.get_user_subscription(user_id)
        if sub:
            return jsonify({"subscription": sub}), 200
        return jsonify({"subscription": {"tier": "free"}}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch subscription: {str(e)}"}), 500
