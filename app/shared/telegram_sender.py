from app.shared.message_sender import MessageSender
import requests
import logging
from threading import Thread
from app.services.openai_service import generate_response, run_assistant_background
from app.utils.gsc_utils import upload_to_gcs_and_get_url
from app.db.message_dao import save_message

class TelegramSender(MessageSender):
    def __init__(self, bot_token, app_id=None, subscription=None):
        self.token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.app_id = app_id
        self.subscription = subscription or {"tier": "free"}

    def send_text(self, chat_id, message):
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        try:
            res = requests.post(url, json=payload)
            res.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {e}")
            return False
        
    def handle_assistant_reply(self,chat_id, thread_id, reply):
        save_message(
            app_id=self.app_id,
            platform="telegram",
            thread_id=thread_id,
            chat_id=str(chat_id),
            content=reply,
            message_type="text",
            direction="right",
            role="assistant"   
        )
        return self.send_text(chat_id, reply)

    def handle_message(self, data):
        """
        Processes incoming Telegram webhook data.
        Returns a response object (e.g. reply message or action)
        """
        if "message" not in data:
            logging.warning("No message in Telegram payload.")
            return None

        message = data["message"]
        chat_id = message["chat"]["id"]
        user_text = message.get("text", "")
        user_name = message["from"].get("first_name", "User")

        logging.info(f"Received message from {user_name}: {user_text} {message}")

        content = ""
        message_type = "text"
        image_path = None
        doc_path = None
        # Handle commands
        if user_text.startswith("/"):
            command = user_text.split()[0].lower()
            reply = self.handle_command(command, user_name)
            self.send_text(chat_id, reply)
        else:
            # Default fallback message
            try:
                if "text" in message:
                    content = user_text
                elif "photo" in message:
                    content = message.get("caption", "Describe this image")
                    message_type = "image"
                    image_path = self.get_public_url(message.get("photo")[-1]["file_id"]) #get last photo file id
                    logging.info(f"Imgur public url: {image_path}")
                    
                elif "document" in message:
                    content = message.get("caption", "Describe this document")
                    message_type = "document"
                    doc_path = self.get_public_url(message.get("document")["file_id"]) #get last document file id
                    logging.info(f"Document public url: {doc_path}")
                
                #generate response from assistant    
                thread, name = generate_response(message_body=content, wa_id=str(chat_id), name=user_name, image_path=image_path, file_path=doc_path)
            
                Thread(target=run_assistant_background, args=(thread,name, lambda thread_id, reply: self.handle_assistant_reply(chat_id, thread_id, reply))).start()    
                save_message(
                    app_id=self.app_id,
                    platform="telegram",
                    thread_id=thread.id,
                    chat_id=str(chat_id),
                    content=content,
                    message_type=message_type,
                    file_url=image_path if message_type == "image" else doc_path
                )
            except Exception as e:
                logging.info(f"Unable to process message: {e}")
                
    
    def handle_command(self, command, name="User"):
        command_map = {
            "/start": f"Hello {name}! Welcome to this bot.",
            "/help": (
                "Here are some things you can try:\n"
                "/start - Start the bot\n"
                "/help - Show this help message\n"
                "/about - Learn about this bot"
            ),
            "/about": "This bot is powered by Python, Flask, and Telegram Bot API."
        }

        return command_map.get(command, f"Sorry, I don't recognize the command `{command}`.")
    
    def get_public_url(self, file_id):
        # Step 1: Get file path
        response = requests.get(f"{self.api_url}/getFile", params={"file_id": file_id})
        response.raise_for_status()
        file_path = response.json()["result"]["file_path"]
        mime_type = response.json()["result"].get("mime_type", None)

        # Step 2: Download the file
        download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        
        logging.info(f"Download url: {download_url}")
        file_response = requests.get(download_url)
        file_response.raise_for_status()
       
        public_url =  upload_to_gcs_and_get_url(file_bytes=file_response.content, folder_name=f"telegram-{self.token}", filename=file_path, content_type=mime_type)
        return public_url
    
    