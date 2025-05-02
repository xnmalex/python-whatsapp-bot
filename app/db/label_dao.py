from app.db.firestore_helper import get_collection
from google.cloud.firestore_v1 import FieldFilter
from datetime import datetime

labels_ref = get_collection("contact_labels")

# Assign multiple contacts to a single label in batch
def assign_label_to_contacts(label, contact_ids, platform, user_id):
    now = datetime.utcnow().isoformat()
    label_doc = labels_ref.document(label).get()

    if label_doc.exists:
        raise ValueError("Label name already exists")

    batch = labels_ref._client.batch()

    for contact_id in contact_ids:
        doc_ref = labels_ref.document()
        batch.set(doc_ref, {
            "label": label,
            "contact_id": contact_id,
            "platform": platform,
            "user_id": user_id,
            "created_at": now
        })

    batch.commit()

# Retrieve contacts by label
def get_contacts_by_label(label, platform, user_id, limit=20, start_after=None):
    query = labels_ref.where(filter=FieldFilter("label", "==", label)) \
                      .where(filter=FieldFilter("platform", "==", platform)) \
                      .where(filter=FieldFilter("user_id", "==", user_id)) \
                      .order_by("created_at").limit(limit)

    if start_after:
        query = query.start_after({"created_at": start_after})

    return [doc.to_dict() for doc in query.stream()]