from flask import Blueprint, request, jsonify
from app.db.user_dao import get_user_by_id, update_user, delete_user
from app.utils.timestamp_utils import update_timestamp
import jwt
import os

profile_blueprint = Blueprint("profile", __name__, url_prefix="/api/v1/profile")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")

def get_user_id_from_token():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub"), payload.get("role")
    except Exception:
        return None, None


@profile_blueprint.route("/update", methods=["PATCH"])
def update_profile():
    user_id, _ = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Invalid or missing token"}), 401

    data = request.get_json()
    allowed_fields = ["name", "subscription"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400

    update_data.update(update_timestamp())
    update_user(user_id, update_data)
    return jsonify({"message": "Profile updated successfully"})


@profile_blueprint.route("/me", methods=["GET"])
def get_profile():
    user_id, _ = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Invalid or missing token"}), 401

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.pop("password", None)
    return jsonify({"user": user})


@profile_blueprint.route("/subscription", methods=["GET"])
def get_subscription():
    user_id, _ = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Invalid or missing token"}), 401

    user = get_user_by_id(user_id)
    return jsonify({"subscription": user.get("subscription", {})})


@profile_blueprint.route("/subscription", methods=["POST"])
def update_subscription():
    user_id, _ = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Invalid or missing token"}), 401

    data = request.get_json()
    subscription = data.get("subscription")
    if not subscription:
        return jsonify({"error": "Missing subscription details"}), 400

    update_user(user_id, {"subscription": subscription, **update_timestamp()})
    return jsonify({"message": "Subscription updated"})


# Admin-only route
@profile_blueprint.route("/admin/delete-user/<user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    _, role = get_user_id_from_token()
    if role != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    delete_user(user_id)
    return jsonify({"message": f"User {user_id} deleted successfully"})
