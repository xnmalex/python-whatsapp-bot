from flask import Blueprint, request, jsonify, g
from app.decorators.auth_decorators import auth_required
from app.db.message_dao import get_messages_by_chat_id, get_message_threads_by_app_id

message_blueprint = Blueprint("message_routes", __name__, url_prefix="/api/v1/messages")


@message_blueprint.route("", methods=["GET"])
@auth_required
def list_app_message_threads():
    try:
        app_id = request.args.get("app_id")
        if not app_id:
            return jsonify({"error": "Missing required parameter: app_id"}), 400

        limit = int(request.args.get("limit", 20))
        start_after = request.args.get("start_after")
        platform_filter = request.args.get("platform")

        print(f"App id: {app_id}")

        # Fetch threads using provided app_id
        threads = get_message_threads_by_app_id(app_id, limit=limit, start_after=start_after)

        # Apply optional platform filter
        if platform_filter:
            threads = [t for t in threads if t.get("platform") == platform_filter]

        has_more = len(threads) == limit
        next_cursor = threads[-1]["created_at"] if has_more else None

        return jsonify({
            "threads": threads,
            "metadata": {
                "limit": limit,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "count": len(threads)
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@message_blueprint.route("/<chat_id>", methods=["GET"])
@auth_required
def get_app_messages(chat_id):
    limit = int(request.args.get("limit", 20))
    start_after = request.args.get("start_after")

    try:
        messages = get_messages_by_chat_id(chat_id, limit=limit, start_after=start_after)
        return jsonify({"messages": messages}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
