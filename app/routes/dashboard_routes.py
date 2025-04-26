from flask import Blueprint, request, jsonify
import os
import jwt
from app.db.metrics_dao import get_summary_metrics, get_all_daily_metrics

admin_dashboard = Blueprint("admin_dashboard", __name__, url_prefix="/api/v1/dashboard")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")

# Simple admin check
def is_admin():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("role") == "admin"
    except Exception:
        return False
    
    
@admin_dashboard.route("/summary", methods=["GET"])
def dashboard_summary():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    data = get_summary_metrics()
    return jsonify({"summary": data}), 200

@admin_dashboard.route("/daily", methods=["GET"])
def dashboard_daily():
    limit = int(request.args.get("limit", 30))
    data = get_all_daily_metrics(limit)
    return jsonify({"daily_stats": data}), 200



