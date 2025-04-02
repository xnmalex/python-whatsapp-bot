import logging
from flask import current_app, jsonify
import json
import requests

from app.services.openai_service import generate_response
import re
import mimetypes

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


# def generate_response(response):
    # Return text in uppercase
    # return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
   
    msg_type = message["type"]

    # TODO: implement custom function here
    # response = generate_response(message_body)
    file_path = None
    public_url = None

    # OpenAI Integration     
    if msg_type == "text":
        message_body = message["text"]["body"]
        response = generate_response(message_body, wa_id, name)
        response = process_text_for_whatsapp(response)
        data = get_text_message_input(wa_id, response)
        send_message(data)

    elif msg_type == "image":
        media_id = message["image"]["id"]
        
        try:
            file_path = download_media_from_whatsapp(media_id, "image/jpeg")
            public_url = upload_to_imgur(file_path)
            logging.info(f"Image uploaded to PostImages: {public_url}")
            
            # Capture the caption if it exists
            caption = message["image"].get("caption", "Describe this image")
            response = generate_response(caption, wa_id, name, image_path=public_url)
            data = get_text_message_input(wa_id, response)
            send_message(data)
        except Exception as e:
            logging.info(f"Failed to process your image. {e}")
            #send_message(fallback)
    elif msg_type == "document":
        media_id = message["document"]["id"]
        mime_type = message["document"].get("mime_type")
        file_path = download_media_from_whatsapp(media_id, mime_type)
    
        try:  
            # Capture the caption if it exists
            caption = message["document"].get("caption", "Describe this document")
            response = generate_response(caption, wa_id, name, file_path=file_path)
            data = get_text_message_input(wa_id, response)
            send_message(data)
        except Exception as e:
            logging.info(f"Failed to process your document.{e}")
        
    else:
        fallback = get_text_message_input(wa_id, "Sorry, I can only process text, images, or documents.")
        send_message(fallback)

def download_media_from_whatsapp(media_id, mime_type):
    ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
    ALLOWED_DOC_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
        "text/plain",
        "text/csv"
    }
    # Step 1: Get media URL
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{media_id}"
    
    logging.info(url)
    
    if mime_type not in ALLOWED_IMAGE_TYPES and mime_type not in ALLOWED_DOC_TYPES:
        raise Exception(f"Unsupported image/document type: {mime_type}")

    res = requests.get(url, headers=headers).json()
    media_url = res["url"]
    
    if not media_url:
        raise Exception("No file URL returned by WhatsApp Graph API.")

    # Step 2: Download actual media file
    media_resp = requests.get(media_url, headers=headers)
    extension = mimetypes.guess_extension(mime_type) or ".bin"  # You can improve with mime type detection
    path = f"/tmp/media_{media_id}{extension}"
    
    logging.info(f"temp media path: {path}")

    with open(path, "wb") as f:
        f.write(media_resp.content)

    return path 
    
def upload_to_imgur(image_path):
    headers = {"Authorization": f"Client-ID 23fab5eea475c19"}
    with open(image_path, "rb") as img:
        response = requests.post(
            "https://api.imgur.com/3/image",
            headers=headers,
            files={"image": img}
        )
    data = response.json()
    if data.get("success"):
        return data["data"]["link"]
    else:
        raise Exception(f"Imgur upload failed: {data}")
    

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
