from app.db.firestore_helper import get_collection
from datetime import datetime

blacklist_ref = get_collection("blacklisted_tokens")

def blacklist_token(token, expires_at_unix):
    # Save with TTL using Firestore timestamp
    blacklist_ref.document(token).set({
        "token": token,
        "expires_at": datetime.utcfromtimestamp(expires_at_unix)
    })

def is_token_blacklisted(token):
    doc = blacklist_ref.document(token).get()
    return doc.exists