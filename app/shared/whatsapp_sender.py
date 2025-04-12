from app.shared.message_sender import MessageSender
import requests
import logging
import re
from app.services.openai_service import generate_response, run_assistant_background
from app.db.message_dao import save_message
from app.utils.gsc_utils import upload_to_gcs_and_get_url
from threading import Thread
import mimetypes

class WhatsAppSender(MessageSender):
    def __init__(self, access_token, phone_number_id, version="v22.0"):
        self.token = access_token
        self.phone_number_id = phone_number_id
        self.version = version
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
    
    def handle_message(self, body):
        wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        msg_type = message["type"]

        app_id = "51d07c69-ec1c-4e34-a917-283c1a553f6c"
        doc_path = None
        image_path = None
        content = ""

        # OpenAI Integration 
        try:    
            if msg_type == "text":
                content = message["text"]["body"]
            elif msg_type == "image":
                media_id = message["image"]["id"]
                image_path = self.download_media_from_whatsapp(media_id, "image/jpeg")
                logging.info(f"Image uploaded to PostImages: {image_path}")
                    
                content = message["image"].get("caption", "Describe this image")
            
            elif msg_type == "document":
                media_id = message["document"]["id"]
                mime_type = message["document"].get("mime_type")
                doc_path = self.download_media_from_whatsapp(media_id, mime_type)
                content = message["document"].get("caption", "Describe this document")
                self.send_text(wa_id, "Processing document. Please wait awhile for the reply")
            else:
                self.send_text(wa_id, "Unsupported content")
            
            #generate response from assistant
            if content:    
                thread, name = generate_response(message_body=content, wa_id=wa_id, name=name, image_path=image_path, file_path=doc_path)
                
                save_message(
                    user_id=str(wa_id),
                    app_id=app_id,
                    platform="whatsapp",
                    thread_id=thread.id,
                    chat_id=str(wa_id),
                    content=content,
                    message_type=msg_type,
                    file_url=image_path if msg_type == "image" else doc_path,
                    assistant_reply=None
                )
                
                Thread(target=run_assistant_background, args=(thread,name, lambda reply: self.handle_assistant_reply(wa_id, reply))).start()
            
        except Exception as e:
            logging.info(f"Failed to generate response .{e}")
            response = "unable to process message"
            self.send_text(wa_id, response)
    
    def handle_assistant_reply(self, wa_id, reply):
        reply = self.process_text_for_whatsapp(reply)
        self.send_text(wa_id, reply)
        
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


    def download_media_from_whatsapp(self, media_id, mime_type):
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
            "Authorization": f"Bearer {self.token}",
        }

        url = f"https://graph.facebook.com/{self.version}/{media_id}"
        
        logging.info(url)
        
        if mime_type not in ALLOWED_IMAGE_TYPES and mime_type not in ALLOWED_DOC_TYPES:
            raise Exception(f"Unsupported image/document type: {mime_type}")

        res = requests.get(url, headers=headers).json()
        media_url = res["url"]
        
        if not media_url:
            raise Exception("No file URL returned by WhatsApp Graph API.")

        # Step 2: Download actual media file
        media_resp = requests.get(media_url, headers=headers)
        media_resp.raise_for_status()
        extension = mimetypes.guess_extension(mime_type) or ".bin"

        path =  upload_to_gcs_and_get_url(file_bytes=media_resp.content, folder_name=f"whataspp-{self.phone_number_id}", filename=f"{media_id}{extension}", content_type=mime_type)

        return path 