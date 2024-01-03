"""Google Storage Helpers"""
# Standard imports
from datetime import timedelta
import os
from urllib.parse import urljoin

# Third-party imports

# Local imports
from . import gcp
from . settings import (
    logger,
    GOOGLE_CLOUD_PROJECT, GOOGLE_SIGNING_CREDENTIALS,
    GOOGLE_STORAGE_BUCKET, GOOGLE_STORAGE_FOLDER,
    MAX_CONTENT_MB, TMPDIR,
)
from .utils import (
    idhash, tznow,
)
from werkzeug.utils import secure_filename


def _client(project_id=GOOGLE_CLOUD_PROJECT, credentials=None):
    """Get a Google Storage client"""
    from google.cloud import storage
    credentials = credentials or gcp.credentials()
    return storage.Client(
        project=str(project_id), credentials=credentials)


def bucket_exists(bucket=GOOGLE_STORAGE_BUCKET):
    """Check to see if a bucket exists"""
    return _client().lookup_bucket(bucket) is not None


def get(name, path=TMPDIR, folder=GOOGLE_STORAGE_FOLDER,
        bucket=GOOGLE_STORAGE_BUCKET,
        project_id=GOOGLE_CLOUD_PROJECT, **kwargs):
    """Download a file from Google Cloud Storage"""
    from google.api_core.exceptions import NotFound

    blob = ref(name=name, folder=folder, bucket=bucket,
               project_id=project_id, **kwargs)

    assert blob.name
    filename = secure_filename(blob.name.split("/")[-1].strip())

    if os.path.isdir(str(path)):
        fullpath = os.path.join(str(path), filename)
    else:
        fullpath = str(path)

    logger.info("[GS] GET %s (%s)", loc(blob), fullpath)

    try:
        blob.download_to_filename(fullpath)
    except NotFound:
        logger.warning("[GS] NOT FOUND: %s", loc(blob))

        # check for a single file using this prefix and download that instead
        try:
            blobs = list(blob.client.list_blobs(blob.bucket, prefix=blob.name))
            if len(blobs) == 1:
                logger.info("[GS] GET %s (%s)", loc(blobs[0]), fullpath)
                blobs[0].download_to_filename(fullpath)
        except NotFound:
            logger.warning("[GS] NOT FOUND: %s/*", loc(blob))
            fullpath = None

    return fullpath


def has(name, folder=GOOGLE_STORAGE_FOLDER, bucket=GOOGLE_STORAGE_BUCKET,
        project_id=GOOGLE_CLOUD_PROJECT, **kwargs):
    """Check to see if file exists in Google Cloud Storage"""
    blob = ref(name=name, folder=folder, bucket=bucket,
               project_id=project_id, **kwargs)
    exists = blob.exists()

    logger.info("[GS] HAS? %s (%s)", loc(blob), exists)

    return exists


def info(name, folder=GOOGLE_STORAGE_FOLDER, bucket=GOOGLE_STORAGE_BUCKET,
         project_id=GOOGLE_CLOUD_PROJECT, **kwargs):
    """Get info about a file in Google Cloud Storage"""
    blob = ref(name=name, folder=folder, bucket=bucket,
               project_id=project_id, **kwargs)

    logger.info("[GS] INFO %s", loc(blob))

    return blob


def loc(obj):
    """Determine location of object"""
    assert hasattr(obj, "bucket") and hasattr(obj, "name")
    return f"gs://{obj.bucket.name}/{obj.name}"


def put(path, name=None, folder=GOOGLE_STORAGE_FOLDER,
        bucket=GOOGLE_STORAGE_BUCKET,
        project_id=GOOGLE_CLOUD_PROJECT, **kwargs):
    """Upload a file to Google Cloud Storage"""
    blob = ref(name=name or path, folder=folder, bucket=bucket,
               project_id=project_id, **kwargs)

    logger.info("[GS] PUT %s (%s)", loc(blob), path)

    blob.upload_from_filename(path)

    return loc(blob)


def ref(name, load=False, folder=GOOGLE_STORAGE_FOLDER,
        bucket=GOOGLE_STORAGE_BUCKET, project_id=GOOGLE_CLOUD_PROJECT,
        credentials=None, **kwargs):
    """Helper to resolve a blob object from params
    :param name: Location of blob: relative path or full URI
    :param load: Load blob metadata and properties from Google Cloud Storage
    :param folder: Optional folder name
    :param bucket: Optional bucket name
    :param project_id: Optional project ID
    :param credentials: Optional credentials
    :param kwargs: Optional keyword arguments (used to generate folder name)
    :return: Tuple of (bucket, blob, URI)"""
    client = _client(project_id=project_id, credentials=credentials)
    bucket_obj = None
    blob = None

    if name.startswith("gs://"):
        parts = name[5:].split("/", 1)
        bucket = parts[0]
        name = "/" + parts[1] if len(parts) > 1 else ""

    bucket_obj = client.get_bucket(str(bucket))

    # if name is a local file then just get the immediate filename
    if os.path.exists(str(name)):
        name = name.split("/")[-1] if "/" in name else str(name)

    # determine folder name in Google Cloud Storage bucket
    # (generate based on hash of ID fields in kwargs if unspecified)
    folder = str(folder) or idhash(**kwargs)    

    # relative URL cannot start with '/'
    relurl = urljoin(folder, name)
    if relurl.startswith("/"):
        relurl = relurl[1:]

    # construct `blob` that represents file on Google Cloud Storage
    blob = None
    if load:  # attempt to load metadata and properties from GCS?
        # NOTE: can use `.reload()` later to refresh from GCS
        blob = bucket_obj.get_blob(relurl)

    if blob is None:
        blob = bucket_obj.blob(relurl)

    logger.debug("[GS] BLOB: name=%s, folder=%s, bucket=%s",
                 name, folder, bucket)

    return blob


def signed_url(name, method="PUT", expiration=60 * 15,
               folder=GOOGLE_STORAGE_FOLDER, bucket=GOOGLE_STORAGE_BUCKET,
               project_id=GOOGLE_CLOUD_PROJECT, credentials=None,
               **kwargs):
    """Get a signed URL for a file in Google Cloud Storage
    :param name: Location of blob: relative path or full URI
    :param method: HTTP method (e.g., PUT, GET, DELETE)
    :param expiration: Expiration time for signed URL in seconds
    :param folder: Optional folder name
    :param bucket: Optional bucket name
    :param project_id: Optional project ID
    :param credentials: Optional credentials to use for signing
    :param kwargs: Additional metadata
    """
    blob = ref(name=name, folder=folder, bucket=bucket,
               project_id=project_id, **kwargs)

    logger.info("[GS] SIGNED %s URL: %s (%s seconds)",
                method, loc(blob), expiration)

    # BUG: headers MUST be ASCII otherwise the signing fails
    headers = {}
    for key, value in kwargs.items():
        header_key = "x-goog-meta-" + key.lower().replace("_", "-")
        headers[header_key] = str(value)
        logger.debug("[GS] SIGNED %s URL %s=%s", method, header_key, value)

    return blob.generate_signed_url(
        credentials=credentials or gcp.signing_credentials(),
        expiration=timedelta(seconds=expiration),
        headers=headers,
        method=method,
        version="v4",
    )


def upload_policy(name, folder=GOOGLE_STORAGE_FOLDER,
                  bucket=GOOGLE_STORAGE_BUCKET,
                  project_id=GOOGLE_CLOUD_PROJECT,
                  **kwargs):
    """Create a signed upload form for a file in Google Cloud Storage"""

    # https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.bucket.Bucket#google_cloud_storage_bucket_Bucket_generate_upload_policy

    blob = ref(name=name, folder=folder, bucket=bucket,
                project_id=project_id, **kwargs)

    logger.info("[GS] UPLOAD FORM: %s", loc(blob))

    conditions = [
        ["eq", "$key", blob.name],
        ["starts-with", "$x-goog-meta-original-filename", ""],
        ["content-length-range", 1, int(MAX_CONTENT_MB) * 1024 * 1024],
    ]

    policy = blob.bucket.generate_upload_policy(
        credentials=gcp.signing_credentials(),
        conditions=conditions,
        expiration=tznow() + timedelta(hours=1))

    policy["key"] = blob.name

    return policy
