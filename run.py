import logging

from app import create_app
from flask_cors import CORS

app = create_app()

CORS(app, resources={
    r"/api/*": {
        "origins": "https://chatagent.tech",
        "supports_credentials": True
    }
})

if __name__ == "__main__":
    logging.info("Flask app started")
    app.run(host="0.0.0.0", port=8000)
