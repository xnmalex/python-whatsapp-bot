from functools import wraps
from flask import request, current_app, g, jsonify
from app.utils.jwt_utils import decode_token
from app.db.user_dao import get_user_by_id
import logging
import hashlib
import hmac

def validate_signature(payload, signature):
    """
    Validate the incoming payload's signature against our expected signature
    """
    # Use the App Secret to hash the payload
    expected_signature = hmac.new(
        bytes(current_app.config["APP_SECRET"], "latin-1"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Check if the signature matches
    return hmac.compare_digest(expected_signature, signature)

def signature_required(f):
    """
    Decorator to ensure that the incoming requests to our webhook are valid and signed with the correct signature.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        signature = request.headers.get("X-Hub-Signature-256", "")[
            7:
        ]  # Removing 'sha256='
        if not validate_signature(request.data.decode("utf-8"), signature):
            logging.info("Signature verification failed!")
            return jsonify({"status": "error", "message": "Invalid signature"}), 403
        return f(*args, **kwargs)

    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Missing or invalid token"}), 401

        token = auth_header.split(" ")[1]
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            user = get_user_by_id(user_id)

            if not user or user.get("role") != "user":
                return jsonify({"success": False, "message": "Unable to find user"}), 403

            g.current_user = user  # store user for downstream use
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 401

        return f(*args, **kwargs)

    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Missing or invalid token"}), 401

        token = auth_header.split(" ")[1]
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            user = get_user_by_id(user_id)

            if not user or user.get("role") != "admin":
                return jsonify({"success": False, "message": "Admin access required"}), 403

            g.current_user = user  # store user for downstream use
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 401

        return f(*args, **kwargs)

    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Missing or invalid token"}), 401

        token = auth_header.split(" ")[1]
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            user = get_user_by_id(user_id)

            if not user or user.get("role") != "super_admin":
                return jsonify({"success": False, "message": "Super Admin access required"}), 403

            g.current_user = user  # store user for downstream use
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 401

        return f(*args, **kwargs)

    return decorated_function
