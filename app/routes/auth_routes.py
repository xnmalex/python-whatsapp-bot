from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os

from app.db.user_dao import create_user, get_user_by_email  # Firestore-based
from app.db.token_blacklist import is_token_blacklisted, blacklist_token

# Replace with your secure key or load from environment
JWT_SECRET = os.environ.get("JWT_SECRET", "supersecret")
JWT_EXP_DELTA = timedelta(minutes=120)
MIN_PASSWORD_CHARACTER = 8

auth_blueprint = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

# Helper function to create JWT

def create_token(user_id, role):
    payload = {
        "sub": user_id,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + JWT_EXP_DELTA
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token

def create_refresh_token(user_id, role, expires_in_days=30):
    payload = {
        "user_id": user_id,
        "role": role,
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=expires_in_days),
        "iat": datetime.utcnow()
    }

    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@auth_blueprint.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if not email or not password or not name:
        return jsonify({"error": "Missing required fields: email, password, name"}), 400

    if len(password) < MIN_PASSWORD_CHARACTER:
        return jsonify({"error": "Password must be at least {MIN_PASSWORD_CHARACTER} characters"}), 400

    if get_user_by_email(email):
        return jsonify({"error": "User already exists"}), 400

    hashed = generate_password_hash(password)
    user = create_user(email, hashed, name)

    return jsonify({"message": "User registered successfully", "user_id": user["user_id"]})

@auth_blueprint.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_token(user["user_id"], user["role"])
    refresh_token = create_refresh_token(user["user_id"], user["role"])

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user["user_id"],
        "email": user["email"],
        "role": user["role"],
    })

@auth_blueprint.route("/refresh", methods=["POST"])
def refresh_token():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
            return jsonify({"error": "Missing refresh token"}), 400
    if is_token_blacklisted(token):
            return jsonify({"error": "Token blacklisted"}), 403
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        print(payload)
        if payload.get("type") != "refresh":
            return jsonify({"error": "Invalid refresh token type"}), 400
        
        new_token = create_token(payload["user_id"], payload["role"])
        blacklist_token(token, payload["exp"])  # add old token to blacklist
        return jsonify({"access_token": new_token})
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": f"error: {e}"}), 400

@auth_blueprint.route("/logout", methods=["POST"])
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()

    if not token:
        return jsonify({"error": "Missing token"}), 400

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        expires_at = payload.get("exp")
        if expires_at:
            blacklist_token(token, expires_at)
            return jsonify({"message": "Successfully logged out"}), 200
        else:
            return jsonify({"error": "Token missing expiry"}), 400
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
