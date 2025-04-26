from flask import Blueprint, request, jsonify
from datetime import datetime
from app.db.contact_dao import (
    save_contact,
    save_contacts_batch,
    get_contact_by_id,
    list_contacts_by_app,
    update_contact,
    delete_contact,
    list_contacts_by_platform
)

contact_routes = Blueprint("contact_routes", __name__, url_prefix="/api/v1/contacts")

@contact_routes.route("/", methods=["POST"])
def create_contact():
    data = request.json
    contact = save_contact(
        app_id=data.get("app_id"),
        platform=data.get("platform"),
        chat_id=data.get("chat_id"),
        phone_number=data.get("phone_number"),
        telegram_username=data.get("telegram_username")
    )
    return jsonify({"message": "Contact created", "data": contact}), 201

@contact_routes.route("/batch", methods=["POST"])
def create_contacts_batch():
    data = request.json
    app_id = data.get("app_id")
    platform = data.get("platform")
    contacts = data.get("contacts", [])

    save_contacts_batch(app_id=app_id, platform=platform, contacts=contacts)
    return jsonify({"message": "Contacts batch saved", "count": len(contacts)}), 200

@contact_routes.route("/<app_id>/<platform>/<chat_id>", methods=["GET"])
def get_contact(app_id, platform, chat_id):
    contact = get_contact_by_id(app_id, platform, chat_id)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(contact), 200

@contact_routes.route("/<app_id>", methods=["GET"])
def list_contacts(app_id):
    platform = request.args.get("platform")
    limit = int(request.args.get("limit", 20))
    start_after = request.args.get("start_after")

    if platform:
        contacts = list_contacts_by_platform(app_id, platform, limit=limit, start_after=start_after)
    else:
        contacts = list_contacts_by_app(app_id, limit=limit, start_after=start_after)
    return jsonify(contacts), 200

@contact_routes.route("/<app_id>/<platform>/<chat_id>", methods=["PATCH"])
def update_contact_route(app_id, platform, chat_id):
    updates = request.json
    success = update_contact(app_id, platform, chat_id, updates)
    if success:
        return jsonify({"message": "Contact updated"}), 200
    return jsonify({"error": "Contact not found"}), 404

@contact_routes.route("/<app_id>/<platform>/<chat_id>", methods=["DELETE"])
def delete_contact_route(app_id, platform, chat_id):
    success = delete_contact(app_id, platform, chat_id)
    if success:
        return jsonify({"message": "Contact deleted"}), 200
    return jsonify({"error": "Contact not found"}), 404
