import uuid
from google.cloud import storage
from google.api_core.exceptions import NotFound, Forbidden, GoogleAPICallError, ServiceUnavailable
import logging
from urllib.parse import urlparse

BUCKET_NAME = "chatagent-cs"

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

def delete_from_gcs(public_url):
    try:
        if not public_url:
            return False

        # Extract the blob name from the public URL
        parsed_url = urlparse(public_url)
        blob_path = parsed_url.path.lstrip("/")  # Remove leading slash

        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_path)

        if blob.exists():
            blob.delete()
            return True
        else:
            return False

    except Exception as e:
        print(f"Error deleting from GCS: {e}")
        return False
