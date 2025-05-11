from app.db.firestore_helper import get_collection
from datetime import datetime, timezone

blacklist_ref = get_collection("blacklisted_tokens")

def blacklist_token(token, expires_at_unix):
    # Save with TTL using Firestore timestamp
    blacklist_ref.document(token).set({
        "token": token,
        "expires_at": datetime.fromtimestamp(expires_at_unix)
    })

def is_token_blacklisted(token):
    doc = blacklist_ref.document(token).get()
    return doc.exists

def is_user_blacklisted(user_id):
    doc = blacklist_ref.document(user_id).get()
    return doc.exists

def blacklist_all_tokens_for_user(user_id):
    # Optional: Clear old ones first, or set TTL
    now = datetime.now(timezone.utc)
    blacklist_ref.document(user_id).set({
        "blacklisted": True,
        "timestamp": now
    })