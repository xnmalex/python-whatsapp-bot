from flask import Blueprint,request, jsonify
from app.services.openai_service import (
    list_assistant,
    create_assistant,
    delete_assistant,
    update_assistant,
    cancel_run_assistant
)
import jwt
import os

assistant_blueprint = Blueprint("assistant", __name__, url_prefix="/api/v1/assistant")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")

def get_user_id_from_token():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None

@assistant_blueprint.route("", methods=["GET"])
def assistant_get():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    return list_assistant()

@assistant_blueprint.route("", methods=["POST"])
def assistant_post():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    return create_assistant()


@assistant_blueprint.route("/<assistant_id>", methods=["DELETE"])
def assistant_delete(assistant_id):
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    return delete_assistant(assistant_id)

@assistant_blueprint.route("/<assistant_id>", methods=["PUT"])
def assistant_put(assistant_id):
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    return update_assistant(assistant_id)


@assistant_blueprint.route("/cancel-run", methods=["POST"])
def cancel_run():
    user_id = get_user_id_from_token()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    return cancel_run_assistant()