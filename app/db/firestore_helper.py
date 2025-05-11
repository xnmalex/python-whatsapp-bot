import os
from google.cloud import firestore
from google.oauth2 import service_account

# Reuse Firestore client and project config
db_host = os.getenv("FIRESTORE_EMULATOR_HOST")
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
credentials = service_account.Credentials.from_service_account_file("secrets/firebase-key.json")

if db_host:
    os.environ["FIRESTORE_EMULATOR_HOST"] = db_host
    _client = firestore.Client(project=project_id)
else:
    _client = firestore.Client(credentials=credentials, project=project_id, database="chatagent")

def get_firestore_client():
    return _client

def get_collection(name):
    return _client.collection(name)
