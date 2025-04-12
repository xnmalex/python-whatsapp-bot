import uuid
from google.cloud import storage
from google.api_core.exceptions import NotFound, Forbidden, GoogleAPICallError, ServiceUnavailable
import logging

def upload_to_gcs_and_get_url(file_bytes, bucket_name="chatagent-cs", folder_name="media", filename="file", content_type="application/octet-stream"):
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        blob_name = f"{folder_name}/{uuid.uuid4()}_{filename}"
        blob = bucket.blob(blob_name)

        blob.upload_from_string(file_bytes, content_type=content_type)
        blob.make_public()  # Optional: if you want to avoid signed URLs

        return blob.public_url
    except NotFound as e:
        logging.error(f"GCS Error: Bucket or blob not found - {e}")
        raise

    except Forbidden as e:
        logging.error(f"GCS Error: Access forbidden - {e}")
        raise

    except ServiceUnavailable as e:
        logging.error(f"GCS Error: Service unavailable - {e}")
        raise

    except GoogleAPICallError as e:
        logging.error(f"GCS API Error - {e}")
        raise

    except Exception as e:
        logging.error(f"Unexpected error during GCS upload: {e}")
        raise
