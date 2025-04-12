import logging
import json
from app.db.message_dao import update_message_by_thread

def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )
    
def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )


def save_assistant_reply(thread_id: str, reply: str) -> None:
    """
    Update the saved message record in Firestore with assistant reply using thread_id.
    """
    try:
        update_message_by_thread(thread_id, {"assistant_reply": reply})
        logging.info(f"Assistant reply saved for thread {thread_id}")
    except Exception as e:
        logging.error(f"Failed to update assistant reply for thread {thread_id}: {e}")