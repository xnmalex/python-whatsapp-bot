from flask import Blueprint, request, jsonify
from app.db import subscription_dao
from app.decorators.auth_decorators import super_admin_required

admin_subscription_bp = Blueprint("admin_subscription", __name__, url_prefix="/api/v1/super-admin/subscriptions")

@admin_subscription_bp.route("", methods=["POST"])
@super_admin_required
def create_subscription():
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
        subscription_dao.create_subscription(tier, price, level, duration_days)
        return jsonify({"message": f"Subscription tier '{tier}' created."}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create subscription: {str(e)}"}), 500


@admin_subscription_bp.route("", methods=["GET"])
@super_admin_required
def get_all_subscriptions():
    try:
        results = subscription_dao.list_subscriptions()
        return jsonify({"subscriptions": results}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch subscriptions: {str(e)}"}), 500


@admin_subscription_bp.route("/<plan_id>", methods=["PATCH"])
@super_admin_required
def update_subscription(plan_id):
    data = request.get_json()
    updates = {}
    if "price" in data:
        updates["price"] = data["price"]
    if "duration_days" in data:
        updates["duration_days"] = data["duration_days"]
    if "level" in data:
        updates["level"] = data["level"]

    if not updates:
        return jsonify({"error": "No valid fields to update."}), 400

    try:
        subscription_dao.update_subscription(plan_id, {**updates})
        return jsonify({"message": f"Subscription updated."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update subscription: {str(e)}"}), 500


@admin_subscription_bp.route("/<tier>", methods=["DELETE"])
@super_admin_required
def delete_subscription(tier):
    try:
        subscription_dao.delete_subscription(tier)
        return jsonify({"message": f"Subscription tier '{tier}' deleted."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete subscription: {str(e)}"}), 500
