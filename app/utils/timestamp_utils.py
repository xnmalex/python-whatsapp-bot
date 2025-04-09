from datetime import datetime


def get_timestamps():
    now = datetime.utcnow().isoformat()
    return {
        "created_at": now,
        "updated_at": now
    }


def update_timestamp():
    return {"updated_at": datetime.utcnow().isoformat()}
