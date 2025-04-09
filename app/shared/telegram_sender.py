from app.shared.message_sender import MessageSender
import requests
import logging

class TelegramSender(MessageSender):
    def __init__(self, bot_token):
        self.token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

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

        logging.info(f"Received message from {user_name}: {user_text}")

        # Handle commands
        if user_text.startswith("/"):
            command = user_text.split()[0].lower()
            reply = self.handle_command(command, user_name)
        else:
            # Default fallback message
            reply = f"You said: {user_text}"

        return self.send_text(chat_id, reply)
    
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