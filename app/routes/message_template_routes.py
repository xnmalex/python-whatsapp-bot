from flask import Blueprint, request, jsonify, g
from app.middleware.auth_context import with_app_context
from app.db.message_template_dao import (
    create_template,
    get_template_by_id,
    list_templates_by_app_id,
    update_template,
    delete_template
)

template_routes = Blueprint("template_routes", __name__, url_prefix="/api/v1/templates")

@template_routes.route("", methods=["POST"])
@with_app_context
def create_message_template():
    data = request.json
    name = data.get("name")
    content = data.get("content")
    if not name or not content:
        return jsonify({"error": "name and content are required"}), 400

    template = create_template(app_id=g.app_id, name=name, content=content)
    return jsonify(template), 201

@template_routes.route("", methods=["GET"])
@with_app_context
def list_templates():
    templates = list_templates_by_app_id(g.app_id)
    return jsonify(templates), 200

@template_routes.route("/<template_id>", methods=["GET"])
@with_app_context
def get_template(template_id):
    result = get_template_by_id(template_id)
    return result if isinstance(result, tuple) else (jsonify(result), 200)

@template_routes.route("/<template_id>", methods=["PATCH"])
@with_app_context
def update_template_route(template_id):
    updates = request.json
    result = update_template(template_id, updates)
    return result if isinstance(result, tuple) else (jsonify(result), 200)

@template_routes.route("/<template_id>", methods=["DELETE"])
@with_app_context
def delete_template_route(template_id):
    result = delete_template(template_id)
    return result if isinstance(result, tuple) else (jsonify(result), 200)
