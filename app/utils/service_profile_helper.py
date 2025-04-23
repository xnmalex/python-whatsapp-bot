from app.db.app_dao import get_app_by_id

class ServiceProfileHelper:
    @staticmethod
    def get_credentials(app_id):
        app = get_app_by_id(app_id)
        if not app:
            raise ValueError("App not found")

        waba = app.get("waba_settings", {})
        telegram = app.get("telegram_settings", {})
        openai = app.get("openai_settings", {})

        return {
            "whatsapp": {
                "token": waba.get("token"),
                "phone_number_id": waba.get("phone_number_id")
            },
            "telegram": {
                "token": telegram.get("token")
            },
            "openai": {
                "api_key": openai.get("api_key"),
                "assistant_id": openai.get("assistant_id")
            }
        }
