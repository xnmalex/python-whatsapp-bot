from flask import Blueprint, request, jsonify, g
from app.decorators.auth_decorators import user_required
from app.db.contact_dao import (
    save_contact,
    save_contacts_batch,
    get_contact_by_id,
    list_contacts_by_app,
    update_contact,
    delete_contact,
    list_contacts_by_platform,
)
from app.db.label_dao import assign_label_to_contacts, get_contacts_by_label

contact_routes = Blueprint("contact_routes", __name__, url_prefix="/api/v1/contacts")

ALLOWED_PLATFORMS = {"whatsapp", "telegram"}

def validate_contact_payload(platform, chat_id, name, telegram_username=None):
    if platform not in ALLOWED_PLATFORMS:
        return None, "Invalid platform. Must be 'whatsapp' or 'telegram'"
    if not chat_id:
        return None, "chat_id is required"
    if chat_id and not name:
        return None, "name is required"

    if platform == "whatsapp":
        return {
            "chat_id": chat_id,
            "phone_number": chat_id,
            "telegram_username": None,
            "name": name,
        }, None
    elif platform == "telegram":
        return {
            "chat_id": chat_id,
            "phone_number": None,
            "telegram_username": telegram_username
        }, None
    return None, "Unsupported platform"

@contact_routes.route("/", methods=["POST"])
@user_required
def create_contact():
    data = request.json
    
    user_id = g.current_user["user_id"]
    
    #whatsapp
    chat_id = data.get("chat_id")
    name = data.get("name")
    
    #telegraam
    platform = data.get("platform")
    telegram_username = data.get("telegram_username")
    
    validated, error = validate_contact_payload(platform, chat_id, name, telegram_username)
    if error:
        return jsonify({"error": f"validation error: {error}"}), 400
    try:
        existing = get_contact_by_id(user_id, platform, chat_id)
        if not existing:
            contact = save_contact(
                user_id=user_id,
                platform=platform,
                chat_id=validated["chat_id"],
                name=validated["name"],
                telegram_username=validated["telegram_username"],
            )
            return jsonify({"message": "Contact created", "data": contact}), 201
    except Exception as e:
        return jsonify({"message": f"{e}", "status":"error"}), 400
    return jsonify({"message": "Contact already exists"}), 200

@contact_routes.route("/batch", methods=["POST"])
@user_required
def create_contacts_batch():
    data = request.json
    user_id = g.current_user["user_id"]
    platform = data.get("platform")
        
    contacts = data.get("contacts", [])

    filtered_contacts = []
    for contact in contacts:
        chat_id = contact.get("chat_id")
        telegram_username = contact.get("telegram_username")
        validated, error = validate_contact_payload(platform, chat_id, telegram_username)
        if error:
            continue
        existing = get_contact_by_id(user_id, platform, chat_id)
        if not existing:
            filtered_contacts.append(validated)

    save_contacts_batch(user_id=user_id, platform=platform, contacts=filtered_contacts)
    return jsonify({"message": "Contacts batch saved", "saved_count": len(filtered_contacts), "skipped": len(contacts) - len(filtered_contacts)}), 200

@contact_routes.route("/<platform>/<chat_id>", methods=["GET"])
@user_required
def get_contact(platform, chat_id):
    user_id = g.current_user["user_id"]
    contact = get_contact_by_id(user_id, platform, chat_id)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(contact), 200

@contact_routes.route("/", methods=["GET"])
@user_required
def list_contacts():
    user_id = g.current_user["user_id"]
    platform = request.args.get("platform")
    limit = int(request.args.get("limit", 20))
    start_after = request.args.get("start_after")

    try:
        if platform:
            contacts = list_contacts_by_platform(user_id, platform, limit=limit, start_after=start_after)
        else:
            contacts = list_contacts_by_app(user_id, limit=limit, start_after=start_after)
        return jsonify(contacts), 200
    except Exception as e:
        return jsonify({"status":"error", "message":f"{e}"}), 400
    
@contact_routes.route("/<platform>/<chat_id>", methods=["PATCH"])
@user_required
def update_contact_route(platform, chat_id):
    updates = request.json
    user_id = g.current_user["user_id"]
    success = update_contact(user_id, platform, chat_id, updates)
    if success:
        return jsonify({"message": "Contact updated"}), 200
    return jsonify({"error": "Contact not found"}), 404

@contact_routes.route("/<platform>/<chat_id>", methods=["DELETE"])
@user_required
def delete_contact_route(platform, chat_id):
    user_id = g.current_user["user_id"]
    success = delete_contact(user_id, platform, chat_id)
    if success:
        return jsonify({"message": "Contact deleted"}), 200
    return jsonify({"error": "Contact not found"}), 404

# label chat
@contact_routes.route("/<platform>/label", methods=["POST"])
@user_required
def label_platform_contacts(platform):
    try:
        if platform not in ALLOWED_PLATFORMS:
             return jsonify({"success": False, "message": "Platform not allowed"}), 400
         
        data = request.json
        label = data.get("label")
        contact_ids = data.get("contact_ids")
        user_id = g.current_user["user_id"]

        if not label or not contact_ids:
            return jsonify({"success": False, "message": "Label and contact_ids are required"}), 400
        
        if len(contact_ids) > 100:
            return jsonify({"success": False, "message": "Maximum contacts for label is 100"}), 400

        assign_label_to_contacts(label, list(set(contact_ids)), platform=platform, user_id=user_id)

        return jsonify({"success": True, "message": f"Labeled {len(contact_ids)} contacts."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@contact_routes.route("/<platform>/label/<label>", methods=["GET"])
@user_required
def get_platform_contacts_by_label(platform, label):
    try:
        user_id = g.current_user["user_id"]
        limit = int(request.args.get("limit", 20))
        start_after = request.args.get("start_after")
        raw_contacts = get_contacts_by_label(label=label, platform=platform, user_id=user_id, limit=limit, start_after=start_after)
        
        unique_contacts = {}
        for contact in raw_contacts:
            cid = contact.get("contact_id")
            if cid:
                unique_contacts[cid] = contact
        return jsonify({"success": True, "contacts": list(unique_contacts.values())}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500