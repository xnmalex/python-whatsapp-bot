import os
from google.cloud import firestore

# Reuse Firestore client and project config
db_host = os.getenv("FIRESTORE_EMULATOR_HOST")
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

if db_host:
    os.environ["FIRESTORE_EMULATOR_HOST"] = db_host
    _client = firestore.Client(project=project_id)
else:
    _client = firestore.Client(project=project_id, database="chatagent")

def get_firestore_client():
    return _client

def get_collection(name):
    return _client.collection(name)
