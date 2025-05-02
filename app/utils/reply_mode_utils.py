import logging
from datetime import datetime
from app.db.app_dao import get_app_by_id

def should_reply_to_user(app_id):
    app_data = get_app_by_id(app_id)
    mode = app_data.get("ai_reply_mode", "auto")

    if mode == "off":
        logging.info(f"[AI Reply] Mode is OFF for app {app_id}. Skipping reply.")
        return False

    if mode == "scheduled":
        schedule = app_data.get("scheduled_schedule", {})
        now = datetime.now()
        day = now.strftime('%a').lower()[:3]  # 'mon', 'tue', etc.
        today_schedule = schedule.get(day)

        if not today_schedule:
            logging.info(f"[AI Reply] No schedule for {day}. Skipping reply.")
            return False

        now_time = now.strftime('%H:%M')
        if not (today_schedule["start"] <= now_time <= today_schedule["end"]):
            logging.info(f"[AI Reply] Current time {now_time} outside scheduled window ({today_schedule['start']} - {today_schedule['end']}).")
            return False

    return True
