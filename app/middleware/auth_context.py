from functools import wraps
from flask import request, g, jsonify
from app.db.app_dao import get_app_by_user_id
from app.db.user_subscription_dao import get_user_subscription
from app.utils.jwt_utils import decode_token

def attach_app_context():
    """
    Middleware-like function to attach app_id and subscription to Flask's `g` context
    based on the user_id decoded from JWT.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "Missing token"}), 401

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        app = get_app_by_user_id(user_id)
        if not app:
            return jsonify({"error": "No app registered for this user"}), 403

        subscription = get_user_subscription(user_id) or {"tier": "free"}

        g.user_id = user_id
        g.app_id = app.get("app_id")
        g.subscription = subscription

    except Exception as e:
        return jsonify({"error": str(e)}), 401
        
# Decorator to enforce app context on protected routes
def with_app_context(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        attach_result = attach_app_context()
        if attach_result is not None:
            return attach_result
        return f(*args, **kwargs)
    return wrapper

