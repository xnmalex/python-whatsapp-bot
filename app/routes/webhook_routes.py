import logging
import json
from flask import Blueprint, request, jsonify, current_app
from app.decorators.auth_decorators import signature_required
from app.utils.message_utils import (
    is_valid_whatsapp_message,
)

from app.shared.telegram_sender import TelegramSender
from app.shared.whatsapp_sender import WhatsAppSender
from app.db.app_dao import get_app_by_app_token, get_app_by_waba_phone_id
from flask import g

webhook_blueprint = Blueprint("webhook", __name__)

def handle_message():
    """
    Handle incoming webhook events from the WhatsApp API.

    This function processes incoming WhatsApp messages and other events,
    such as delivery statuses. If the event is a valid message, it gets
    processed. If the incoming payload is not a recognized WhatsApp event,
    an error is returned.

    Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

    Returns:
        response: A tuple containing a JSON response and an HTTP status code.
    """
    body = request.get_json()
    # logging.info(f"request body: {body}")

    # Check if it's a WhatsApp status update
    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        logging.info("Received a WhatsApp status update.")
        return jsonify({"status": "ok"}), 200

    try:
        if is_valid_whatsapp_message(body):
            try:
                phone_number_id = body["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
            except (KeyError, IndexError):
                return jsonify({"error": "Missing phone_number_id in webhook payload"}), 400
            
            app = get_app_by_waba_phone_id(phone_number_id)
            if not app:
                return jsonify({"error": "Invalid phone_number_id or app not found"}), 403

            app_id = app.get("app_id")
            subscription = app.get("subscription", {"tier": "free"})
            
            whatsapp_bot = WhatsAppSender( 
                access_token=current_app.config['ACCESS_TOKEN'],
                phone_number_id=current_app.config['PHONE_NUMBER_ID'],
                app_id = app_id,
                subscription = subscription
            )
            try:
                result = whatsapp_bot.handle_message(body)
                return jsonify({"status": "ok", "result":result}), 200
            except Exception as e:
                logging.exception("Failed to handle WhatsApp message")
                return jsonify({"error": str(e)}), 500
        else:
            # if the request is not a WhatsApp API event, return an error
            return (
                jsonify({"status": "error", "message": "Not a WhatsApp API event"}),
                404,
            )
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400


# Required webhook verifictaion for WhatsApp
def verify():
    # Parse params from the webhook verification request
    logging.info('verify')
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    # Check if a token and mode were sent


    if mode and token:
        # Check the mode and token sent are correct
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            # Respond with 200 OK and challenge token from the request
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            logging.info("VERIFICATION_FAILED")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        # Responds with '400 Bad Request' if verify tokens do not match
        logging.info("MISSING_PARAMETER")
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


@webhook_blueprint.route("/webhook", methods=["GET"])
def webhook_get():
    return verify()

@webhook_blueprint.route("/webhook", methods=["POST"])
@signature_required
def webhook_post():
    return handle_message()

@webhook_blueprint.route("/telegram/webhook", methods=["POST"])
def telegram_webhook_post():   
    try:
        app_token = request.args.get("app_token")
        if not app_token:
            return jsonify({"error": "Missing app_token in query"}), 400

        app = get_app_by_app_token(app_token)
        if not app:
            return jsonify({"error": "Invalid app_token or app not found"}), 403
        
        app_id = app.get("app_id")
        subscription = app.get("subscription", {"tier": "free"})
        
        telegram_bot = TelegramSender(
            current_app.config["TELEGRAM_BOT_TOKEN"], 
            app_id=app_id,
            subscription=subscription
        )
        data = request.get_json()
        result = telegram_bot.handle_message(data)
        
        return jsonify({"status": "ok", "result": result}), 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": "Something went wrong"}), 500


