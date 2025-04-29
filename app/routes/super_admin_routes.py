from flask import Blueprint, request, jsonify
from app.db.user_dao import create_user, get_user_by_email, get_user_by_id, delete_user, list_admins
from app.db.subscription_dao import create_subscription, update_subscription
from app.decorators.auth_decorators import super_admin_required
from app.utils.password_utils import hash_password

super_admin_blueprint = Blueprint("super_admin", __name__)

@super_admin_blueprint.route("/api/v1/super-admin/create-admin", methods=["POST"])
@super_admin_required
def create_admin():
    try:
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
        user_data = create_user(email=email, password_hash=password_hash, name=name, role="admin")

        # Assign permissions if provided
        if permissions:
            user_data["permissions"] = permissions
            from app.db.firestore_helper import get_collection
            users_ref = get_collection("users")
            users_ref.document(user_data["user_id"]).update({"permissions": permissions})

        return jsonify({"success": True, "user": user_data["user_id"]}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@super_admin_blueprint.route("/api/v1/super-admin/delete-admin/<user_id>", methods=["DELETE"])
@super_admin_required
def delete_admin(user_id):
    try:
        user = get_user_by_id(user_id)
        
        print(user)
        if not user or user.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin not found"}), 404

        delete_user(user_id)
        return jsonify({"success": True, "message": "Admin deleted successfully"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@super_admin_blueprint.route("/api/v1/super-admin/list-admins", methods=["GET"])
@super_admin_required
def list_admin():
    try:
        limit = int(request.args.get("limit", 20))
        start_after = request.args.get("start_after", None)

        admins = list_admins(limit=limit, start_after=start_after)
        admin_list = []

        for user in admins:
            user_info = {
                "user_id": user.get("user_id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "created_at": user.get("created_at")
            }
            admin_list.append(user_info)

        return jsonify({"success": True, "admins": admin_list}), 200

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