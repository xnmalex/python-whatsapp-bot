from flask import Blueprint, request, jsonify, g
from app.db.user_dao import get_user_by_id, update_user
from app.db.user_subscription_dao import get_user_subscription
from app.utils.gsc_utils import upload_to_gcs_and_get_url, delete_from_gcs
from app.decorators.auth_decorators import auth_required
from datetime import datetime
from PIL import Image
import io


profile_blueprint = Blueprint("profile", __name__, url_prefix="/api/v1/profile")

@profile_blueprint.route("/me", methods=["GET"])
@auth_required
def get_profile():
    user_id = g.current_user['user_id']
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
     
@profile_blueprint.route("/update", methods=["PUT"])
@auth_required
def update_user_details():
    user_id = g.current_user['user_id']
    if not user_id:
        return jsonify({"error": "Invalid or missing token"}), 401
    
    try:
        data = request.get_json()

        updates = {}
        if "name" in data:
            updates["name"] = data["name"]

        update_user(user_id, updates)

        return jsonify({"success": True, "message": "User updated successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
     
@profile_blueprint.route("/upload", methods=["POST"])
@auth_required
def upload_profile_picture():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "message": "No selected file"}), 400

        user_id = g.current_user['user_id']
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        original_filename = f"{user_id}_{timestamp}.png"
        resized_filename = f"{user_id}_{timestamp}_300x300.png"
        
        # Read file content
        original_bytes = file.read()

        # Upload original image
        original_url = upload_to_gcs_and_get_url(file_bytes=original_bytes, folder_name="profile-pictures", filename=original_filename, content_type=file.mimetype)
        
        # Resize image to 300x300
        image = Image.open(io.BytesIO(original_bytes))
        image = image.convert("RGB")
        image.thumbnail((300, 300))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        resized_url = upload_to_gcs_and_get_url(
            file_bytes=buffer.read(),
            folder_name="profile-pictures",
            filename=resized_filename,
            content_type="image/png"
        )

        # Update user profile
        update_user(user_id, {
            "profile_pic_url": original_url,
            "profile_pic_thumbnail": resized_url
        })

        return jsonify({
            "success": True,
            "profile_pic_url": original_url,
            "thumbnail_url": resized_url
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@profile_blueprint.route("/remove-picture", methods=["PATCH"])
@auth_required
def remove_profile_picture():
    try:
        user_id = g.current_user['user_id']
        user = get_user_by_id(user_id)

        original_url = user.get("profile_pic_url")
        thumbnail_url = user.get("profile_pic_thumbnail")

        if original_url:
            delete_from_gcs(original_url)
        if thumbnail_url:
            delete_from_gcs(thumbnail_url)
            
        update_user(user_id, {
            "profile_pic_url": None,
            "profile_pic_thumbnail": None
        })
        return jsonify({"success": True, "message": "Profile picture removed."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

