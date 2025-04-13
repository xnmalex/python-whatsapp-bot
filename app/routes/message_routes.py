from flask import Blueprint, request, jsonify, g
from app.middleware.auth_context import with_app_context
from app.db.message_dao import get_messages_by_chat_id, get_message_threads_by_app_id

message_blueprint = Blueprint("message_routes", __name__, url_prefix="/api/v1/messages")


@message_blueprint.route("", methods=["GET"])
@with_app_context
def list_app_message_threads():
    limit = int(request.args.get("limit", 20))
    start_after = request.args.get("start_after")
    platform_filter = request.args.get("platform")

    print(f"App id: {g.app_id}")
    try:
       
        threads = get_message_threads_by_app_id(g.app_id, limit=limit, start_after=start_after)
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
@with_app_context
def get_app_messages(chat_id):
    limit = int(request.args.get("limit", 20))
    start_after = request.args.get("start_after")

    try:
        messages = get_messages_by_chat_id(chat_id, limit=limit, start_after=start_after)
        return jsonify({"messages": messages}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
