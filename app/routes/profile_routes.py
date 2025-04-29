from flask import Blueprint, request, jsonify
from app.db.user_dao import get_user_by_id, delete_user
from app.db.user_subscription_dao import get_user_subscription
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


@profile_blueprint.route("/me", methods=["GET"])
def get_profile():
    user_id, _ = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Invalid or missing token"}), 401

    try:
        user = get_user_by_id(user_id)
        subscription = get_user_subscription(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        user.pop("password", None)
        return jsonify({"user": user, "subscription":subscription})
    except Exception as e:
         return jsonify({"status": False, "error":f"{e}"})
    

# Admin-only route
@profile_blueprint.route("/admin/delete-user/<user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    _, role = get_user_id_from_token()
    if role != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    delete_user(user_id)
    return jsonify({"message": f"User {user_id} deleted successfully"})
