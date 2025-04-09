class MessageSender:
    def send_text(self, recipient_id: str, message: str) -> bool:
        raise NotImplementedError("Must be implemented by subclass.")
