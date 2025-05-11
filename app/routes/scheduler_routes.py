from flask import Blueprint, request, jsonify, g
from datetime import datetime, timezone
from app.middleware.auth_context import with_app_context
from app.db.scheduler_dao import (
    create_schedule,
    list_schedules_by_app_id,
    get_schedule_by_id,
    update_schedule,
    delete_schedule,
    get_due_schedules
)
from app.shared.whatsapp_sender import WhatsAppSender
from app.shared.telegram_sender import TelegramSender

scheduler_routes = Blueprint("scheduler_routes", __name__, url_prefix="/api/v1/schedulers")

@scheduler_routes.route("", methods=["POST"])
@with_app_context
def create_scheduled_message():
    data = request.json
    name = data.get("name")
    platform = data.get("platform")
    content = data.get("content")
    send_at = data.get("send_at")
    recipients = data.get("recipients", [])

    if not all([name, platform, content, send_at, recipients]):
        return jsonify({"error": "Missing required fields"}), 400

    schedule = create_schedule(g.app_id, name, platform, content, send_at, recipients)
    return jsonify(schedule), 201

@scheduler_routes.route("", methods=["GET"])
@with_app_context
def list_schedules():
    limit = int(request.args.get("limit", 20))
    start_after = request.args.get("start_after")
    schedules = list_schedules_by_app_id(g.app_id, limit=limit, start_after=start_after)
    return jsonify(schedules), 200

@scheduler_routes.route("/<schedule_id>", methods=["GET"])
@with_app_context
def get_schedule(schedule_id):
    schedule = get_schedule_by_id(schedule_id)
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404
    return jsonify(schedule), 200

@scheduler_routes.route("/<schedule_id>", methods=["PATCH"])
@with_app_context
def update_schedule_route(schedule_id):
    updates = request.json
    success = update_schedule(schedule_id, updates)
    if not success:
        return jsonify({"error": "Schedule not found"}), 404
    return jsonify({"message": "Schedule updated"}), 200

@scheduler_routes.route("/<schedule_id>", methods=["DELETE"])
@with_app_context
def delete_schedule_route(schedule_id):
    success = delete_schedule(schedule_id)
    if not success:
        return jsonify({"error": "Schedule not found"}), 404
    return jsonify({"message": "Schedule deleted"}), 200

# Cloud Scheduler trigger to dispatch messages
@scheduler_routes.route("/dispatch", methods=["POST"])
def dispatch_scheduled_messages():
    now = datetime.now(timezone.utc)
    schedules = get_due_schedules(now)

    for sched in schedules:
        try:
            if sched["platform"] == "whatsapp":
                sender = WhatsAppSender(...)  # Replace with actual init
            elif sched["platform"] == "telegram":
                sender = TelegramSender(...)  # Replace with actual init
            else:
                continue

            for recipient in sched["recipients"]:
                sender.send_text(recipient, sched["content"])

            update_schedule(sched["schedule_id"], {"status": "sent"})
        except Exception as e:
            update_schedule(sched["schedule_id"], {"status": "failed"})

    return jsonify({"message": f"Processed {len(schedules)} scheduled messages."}), 200