from datetime import datetime, timezone
from app.db.firestore_helper import get_collection
from google.cloud.firestore_v1 import FieldFilter
from flask import jsonify

templates_ref = get_collection("message_templates")

# Create a new message template
def create_template(app_id, name, content):
    now = datetime.now(timezone.utc)
    doc_ref = templates_ref.document()
    template = {
        "template_id": doc_ref.id,
        "app_id": app_id,
        "name": name,
        "content": content,
        "created_at": now,
        "updated_at": now
    }
    doc_ref.set(template)
    return template

# Get a template by ID
def get_template_by_id(template_id):
    doc = templates_ref.document(template_id).get()
    if not doc.exists:
        return jsonify({"error": "Template not found"}), 404
    return doc.to_dict()

# List all templates for an app
# List all templates for an app with pagination
def list_templates_by_app_id(app_id, limit=20, start_after=None):
    query = templates_ref.where(filter=FieldFilter("app_id", "==", app_id)).order_by("created_at", direction="DESCENDING").limit(limit)
    if start_after:
        query = query.start_after({"created_at": start_after})
    docs = query.stream()
    templates = [doc.to_dict() for doc in docs]
    return templates


# Update a template
def update_template(template_id, updates):
    doc_ref = templates_ref.document(template_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Template not found"}), 404
    updates["updated_at"] = datetime.now(timezone.utc)
    doc_ref.update(updates)
    return {"message": "Template updated"}

# Delete a template
def delete_template(template_id):
    doc_ref = templates_ref.document(template_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Template not found"}), 404
    doc_ref.delete()
    return {"message": "Template deleted"}
