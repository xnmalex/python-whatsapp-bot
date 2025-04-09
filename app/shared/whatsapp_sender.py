from app.shared.message_sender import MessageSender
import requests
import logging
import re

class WhatsAppSender(MessageSender):
    def __init__(self, access_token, phone_number_id, version="v22.0"):
        self.token = access_token
        self.phone_number_id = phone_number_id
        self.url = f"https://graph.facebook.com/{version}/{self.phone_number_id}/messages"

    def send_text(self, recipient_id, message):
        msg = self.process_text_for_whatsapp(message)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "text": {"preview_url": False, "body": msg},
        }
        
        
        try:
            res = requests.post(self.url, headers=headers, json=data)
            res.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            logging.info("Request failed:", e)
            logging.info("Response:", res.text)
            return False
        
    def process_text_for_whatsapp(self, text):
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


    