from datetime import datetime, timezone

def get_timestamps():
    now = datetime.now(timezone.utc)
    return {
        "created_at": now,
        "updated_at": now
    }


def update_timestamp():
    return {"updated_at": datetime.now(timezone.utc)}
