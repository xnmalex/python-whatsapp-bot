from flask import Blueprint, request,g, jsonify
from app.db.user_dao import create_user, get_user_by_email, get_user_by_id, delete_user, list_admins, list_users, update_user
from app.db.subscription_dao import create_subscription, update_subscription
from app.decorators.auth_decorators import super_admin_required, admin_required, admin_auth_required
from app.utils.password_utils import hash_password
from app.db.token_blacklist import blacklist_token
from app.db.app_dao import fetch_all_apps_with_filters
import logging

super_admin_blueprint = Blueprint("super_admin", __name__)

@super_admin_blueprint.route("/api/v1/super-admin/create-admin", methods=["POST"])
@super_admin_required
def create_admin():
    try:
        creator_id = g.current_user["user_id"]
        data = request.json
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        permissions = data.get("permissions", [])  # list of permissions

        if not email or not password or not name:
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        existing_user = get_user_by_email(email)
        if existing_user:
            return jsonify({"success": False, "message": "Email already exists"}), 400

        password_hash = hash_password(password)
        user_data = create_user(email=email, password_hash=password_hash, name=name, creator_id=creator_id, role="admin")

        # Assign permissions if provided
        if permissions:
            user_data["permissions"] = permissions
            from app.db.firestore_helper import get_collection
            users_ref = get_collection("users")
            users_ref.document(user_data["user_id"]).update({"permissions": permissions})

        return jsonify({"success": True, "user": user_data["user_id"]}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@super_admin_blueprint.route("/api/v1/super-admin/update-admin/<user_id>", methods=["PATCH"])
@super_admin_required
def update_admin(user_id):
    try:
        data = request.get_json()
        name = data.get("name")
        permissions = data.get("permissions")

        #valid admin user id
        user = get_user_by_id(user_id)
        if not user or user.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin user not found"}), 404

        updates = {}
        if name:
            updates["name"] = name
        if permissions is not None:
            updates["permissions"] = permissions

        if not updates:
            return jsonify({"success": False, "message": "No valid fields to update"}), 400

        update_user(user_id, updates)

        return jsonify({"success": True, "message": "Admin updated successfully"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@super_admin_blueprint.route("/api/v1/super-admin/delete-admin/<user_id>", methods=["DELETE"])
@super_admin_required
def delete_admin(user_id):
    try:
        user = get_user_by_id(user_id)
        
        if not user or user.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin not found"}), 404

        delete_user(user_id)
        return jsonify({"success": True, "message": "Admin deleted successfully"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@super_admin_blueprint.route("/api/v1/super-admin/users", methods=["GET"])
@super_admin_required
def list_all_users():
    try:
        limit = int(request.args.get("limit", 20))
        start_after = request.args.get("start_after", None)
        role = request.args.get("role", "admin")

        if role == "admin":
            data = list_admins(limit=limit, start_after=start_after)
        else:
            data = list_users(limit=limit, start_after=start_after)
        user_list = []

        for user in data.get("users", []):
            user_info = {
                "user_id": user.get("user_id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "permissions":user.get("permissions"),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at")
            }
            user_list.append(user_info)

        return jsonify({"success": True, "users": user_list, "total":data.get("total", 0)}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    

@super_admin_blueprint.route("/api/v1/super-admin/create-subscription", methods=["POST"])
@super_admin_required
def create_subscription_plan():
    try:
        data = request.json
        tier = data.get("tier")
        price = data.get("price")
        level = data.get("level")
        duration_days = data.get("duration_days")

        if not tier or price is None or level is None or duration_days is None:
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        plan = create_subscription(tier, price, level, duration_days)
        return jsonify({"success": True, "plan": plan}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@super_admin_blueprint.route("/api/v1/super-admin/update-subscription/<plan_id>", methods=["PATCH"])
@super_admin_required
def update_subscription_plan(plan_id):
    try:
        updates = request.json
        update_subscription(plan_id, updates)
        return jsonify({"success": True, "message": "Subscription plan updated"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@super_admin_blueprint.route("/api/v1/admin/create-user", methods=["POST"])
@admin_required
def create_user_by_admin():
    try:
        creator_id = g.current_user["user_id"]
        data = request.json
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")

        if not email or not password or not name:
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        existing_user = get_user_by_email(email)
        if existing_user:
            return jsonify({"success": False, "message": "Email already exists"}), 400

        password_hash = hash_password(password)
        user_data = create_user(email=email, password_hash=password_hash, name=name, creator_id=creator_id, role="user")

        user_data.pop("password", None)
        return jsonify({"success": True, "user": user_data}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@super_admin_blueprint.route("/api/v1/super-admin/reset-admin-password", methods=["POST"])
@super_admin_required
def super_admin_reset_admin_password():
    data = request.get_json()
    email = data.get("email")
    new_password = data.get("new_password")
    
    if not email or not new_password:
        return jsonify({"success": False, "message": "Missing email or new password"}), 400

    user = get_user_by_email(email)
    if not user or user.get("role") != "admin":
        return jsonify({"success": False, "message": "Target must be an admin"}), 403

    update_user(user["user_id"], {"password": hash_password(new_password)})

    logging.info(f"[Super Admin] Reset admin password for {email}")
    return jsonify({"success": True, "message": f"Password reset for admin {email}"}), 200

@super_admin_blueprint.route("/api/v1/super-admin/apps-with-bots", methods=["GET"])
@admin_auth_required
def super_admin_get_all_apps_with_bots():
    try:
        platform = request.args.get("platform")  # 'whatsapp' or 'telegram'
        if platform not in ["whatsapp", "telegram"]:
            return jsonify({"success": False, "error": "Invalid platform"}), 400

        limit = int(request.args.get("limit", 100))
        start_after = request.args.get("start_after")
        sort_order = request.args.get("sort_order", "asc")

        # Fetch apps filtered by bot type
        apps = fetch_all_apps_with_filters(
            limit=limit,
            start_after_raw=start_after,
            sort_order=sort_order,
            platform=platform
        )

        bots = []

        for app in apps:
            # Select the bot settings object directly
            if platform == "whatsapp":
                bot_settings = app.get("waba_settings")
            elif platform == "telegram":
                bot_settings = app.get("telegram_settings")
            else:
                continue

            if not isinstance(bot_settings, dict) or not bot_settings:
                continue

            bots.append({
                "app_id": app.get("id"),
                "app_name": app.get("name"),
                "owner_id": app.get("owner_id"),
                "owner_name": app.get("owner_name", "Unknown"),
                "platform": platform,
                "total_chat_count": app.get("total_chat_count", 0),
                "openai_settings": app.get("openai_settings", {}),  # include even if empty
                "bot": bot_settings
            })

        return jsonify({"success": True, "bots": bots}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500