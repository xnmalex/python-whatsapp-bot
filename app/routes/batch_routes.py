from flask import Blueprint, request, jsonify, g
from app.middleware.auth_context import with_app_context
from app.db.message_template_dao import get_template_by_id
from app.db.subscription_dao import get_subscription_by_tier
from app.shared.whatsapp_sender import WhatsAppSender
from app.shared.telegram_sender import TelegramSender
from app.utils.service_profile_helper import ServiceProfileHelper

batch_routes = Blueprint("batch_routes", __name__, url_prefix="/api/v1/batch")

@batch_routes.route("/send", methods=["POST"])
@with_app_context
def send_batch_message():
    data = request.json
    platform = data.get("platform")
    content = data.get("content")
    template_id = data.get("template_id")
    recipients = data.get("recipients", [])

    if not platform or not recipients:
        return jsonify({"error": "platform and recipients are required"}), 400

    if template_id:
        template = get_template_by_id(template_id)
        if isinstance(template, tuple):
            return template
        content = template.get("content")

    if not content:
        return jsonify({"error": "Message content is required"}), 400
    
     # Check subscription limit
    subscription = g.subscription
    app_id =g.app_id
    plan = subscription.get("plan")
    if plan:
        message_limit = plan.get("batch_limit", 50)  # default fallback
        if len(recipients) > message_limit:
            return jsonify({"error": f"Your plan allows max {message_limit} messages per batch."}), 403

    creds = ServiceProfileHelper.get_credentials(g.app_id)
    whatsapp = creds.get("whatsapp", {})
    telegram = creds.get("telegram", {})
   
    try:
        if platform == "whatsapp": 
            if whatsapp.get("token") and whatsapp.get("phone_number_id"):
                print(whatsapp)
                sender = WhatsAppSender(access_token=whatsapp.get("token"), phone_number_id=whatsapp.get("phone_number_id"), app_id=app_id,  subscription = subscription)  
            else:
                return jsonify({"error": "whatsapp token or phone number id not found"}), 400
        elif platform == "telegram":
            if telegram.get("token"):
                sender = TelegramSender(access_token=telegram.get("token"), app_id=app_id,  subscription = subscription) 
            else:
                return jsonify({"error": "telegram token not found"}), 400 
        else:
            return jsonify({"error": "Unsupported platform"}), 400

        success_count = 0
        failed_recipients = []
        for r in recipients:
            success = sender.send_text(r, content)
            if success:
                success_count += 1
            else:
                failed_recipients.append(r)

        return jsonify({
            "success": True,
            "message": f"Sent to {success_count} out of {len(recipients)} recipients.",
            "failed": failed_recipients
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
