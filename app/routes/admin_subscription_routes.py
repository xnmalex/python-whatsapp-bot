from flask import Blueprint, request, jsonify
import os
import jwt
from app.db import subscription_dao
from app.utils.timestamp_utils import update_timestamp

admin_subscription_bp = Blueprint("admin_subscription", __name__, url_prefix="/api/v1/admin/subscriptions")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")


# Simple admin check
def is_admin():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("role") == "admin"
    except Exception:
        return False


@admin_subscription_bp.route("", methods=["POST"])
def create_subscription():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    tier = data.get("tier")
    price = data.get("price")
    duration_days = data.get("duration_days", 0)
    level = data.get("level", 1)

    if not tier or price is None:
        return jsonify({"error": "'tier' and 'price' are required."}), 400

    if tier.lower() == "free":
        return jsonify({"error": "The 'free' plan is reserved as the default and cannot be re-created."}), 400

    try:
        if subscription_dao.get_subscription_by_tier(tier):
            return jsonify({"error": f"Subscription tier '{tier}' already exists."}), 400

        if subscription_dao.is_level_conflicting(level):
            return jsonify({"error": f"Another tier already uses level '{level}'. Please choose a unique level."}), 400

        subscription_dao.set_subscription(tier, {
            "tier": tier,
            "price": price,
            "duration_days": duration_days,
            "level": level,
            **update_timestamp()
        })
        return jsonify({"message": f"Subscription tier '{tier}' created."}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create subscription: {str(e)}"}), 500


@admin_subscription_bp.route("", methods=["GET"])
def get_all_subscriptions():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        results = subscription_dao.list_subscriptions()
        return jsonify({"subscriptions": results}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch subscriptions: {str(e)}"}), 500


@admin_subscription_bp.route("/<tier>", methods=["PATCH"])
def update_subscription(tier):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    updates = {}
    if "price" in data:
        updates["price"] = data["price"]
    if "duration_days" in data:
        updates["duration_days"] = data["duration_days"]
    if "level" in data:
        new_level = data["level"]
        if subscription_dao.is_level_conflicting(new_level, exclude_tier=tier):
            return jsonify({"error": f"Another tier already uses level '{new_level}'. Please choose a unique level."}), 400
        updates["level"] = new_level

    if not updates:
        return jsonify({"error": "No valid fields to update."}), 400

    try:
        updates.update(update_timestamp())
        subscription_dao.set_subscription(tier, {**subscription_dao.get_subscription_by_tier(tier), **updates})
        return jsonify({"message": f"Subscription tier '{tier}' updated."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update subscription: {str(e)}"}), 500


@admin_subscription_bp.route("/<tier>", methods=["DELETE"])
def delete_subscription(tier):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        subscription_dao.delete_subscription(tier)
        return jsonify({"message": f"Subscription tier '{tier}' deleted."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete subscription: {str(e)}"}), 500
