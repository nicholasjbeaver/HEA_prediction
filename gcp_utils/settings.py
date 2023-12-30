"""Settings for the web app."""
# Standard library imports
import logging
import os
import re
import threading

# Local imports
from utils import duck_bool


DEBUG = duck_bool(os.getenv("DEBUG", "false"))  # raise exceptions, output more

ENV = os.getenv("ENV", "dev").lower()

CKBASE = "ck" + ENV if ENV != "prod" else "corpuskeeper"

SECRET_PREFIX = os.getenv("SECRET_PREFIX", CKBASE.upper() + "_")

# LAZY SETTINGS follow (they are only evaluated when they are used)
class LazySetting:
    """A lazy setting that is only evaluated when it is used"""
    def __init__(self, name, default=None, local_only=False, not_secret=False,
                 getter=None, thread_safe=False):
        self.name = name
        self.default = default
        self.local_only = local_only
        self.not_secret = not_secret
        self.getter = getter
        self.thread_safe = thread_safe

        # if thread safe: store the value on the same reference for ALL threads
        if thread_safe:
            self._thread_local = self
        # otherwise store the value in thread local storage (TLS)
        else:
            self._thread_local = threading.local()

    def resolve(self):
        if self.getter:
            return self.getter()

        return get_setting(
            self.name,
            default=self.default,
            local_only=self.local_only,
            not_secret=self.not_secret,
        )

    def reset(self):
        self._thread_local.resolved = False
        self._thread_local.value = None

    def set(self, value):
        self._thread_local.value = value
        self._thread_local.resolved = True
        return value

    def get(self, required_resolved=False):
        """Retrieve resolved value or go resolve it and return it"""
        resolved = getattr(self._thread_local, "resolved", False)
        assert resolved or not required_resolved
        value = getattr(self._thread_local, "value", None)

        if resolved or value is not None:
            return self._thread_local.value

        return self.set(self.resolve())

    # WARNING: many comparisons cause this to be evaluated
    # use `if my_setting is not None` instead of `if my_setting`
    def __bool__(self):
        return duck_bool(self.get(), default=self.default)

    def __float__(self):
        return float(self.get())

    def __int__(self):
        return int(self.get())

    def __str__(self):
        s = self.get()
        if s is None:
            return ""
        return s

#
# CONFIGURE LOGGING
#
class TaggedLogger(logging.Logger):
    """Allows for `tag` (and other values) to be added to log messages"""
    def __init__(self, name, level=logging.NOTSET):
        self.threadsafe_storage = threading.local()
        super().__init__(name, level)

    @property
    def tag(self):
        return getattr(self.threadsafe_storage, "tag", "")
    @tag.setter
    def tag(self, tag):
        self.threadsafe_storage.tag = str(tag)

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None,
                   extra=None, sinfo=None):
        if extra is None:
            extra = {}
        if 'tag' not in extra:
            extra['tag'] = self.tag
        return super().makeRecord(name, level, fn, lno, msg, args, exc_info,
                                  func=func, extra=extra, sinfo=sinfo)

# default class to instantiate with getLogger() (supports `.tag` property)
logging.setLoggerClass(TaggedLogger)

# NOTE: date/time is not included since Cloud Run logs already add it
formatter = logging.Formatter('%(levelname)s [%(tag)s] %(message)s')

# configure application `logger`
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(CKBASE)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

#
# SERVER SETTINGS
#
PORT = int(os.getenv("PORT", "2304"))

#
# GOOGLE CLOUD SETTINGS
#
SKIP_GCP = duck_bool(os.getenv("SKIP_GCP", "0"))

def __GOOGLE_CLOUD_PROJECT():
    """Getter for `GOOGLE_CLOUD_PROJECT` setting"""
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not GOOGLE_CLOUD_PROJECT:
        import gcp
        GOOGLE_CLOUD_PROJECT = gcp.detect_project()
        if GOOGLE_CLOUD_PROJECT:
            os.environ["GOOGLE_CLOUD_PROJECT"] = GOOGLE_CLOUD_PROJECT
    return GOOGLE_CLOUD_PROJECT

GOOGLE_CLOUD_PROJECT = LazySetting("GOOGLE_CLOUD_PROJECT", not_secret=True,
                                   getter=__GOOGLE_CLOUD_PROJECT, thread_safe=True)

def __GOOGLE_APPLICATION_CREDENTIALS():
    """Getter for `GOOGLE_APPLICATION_CREDENTIALS` setting"""
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not GOOGLE_APPLICATION_CREDENTIALS:
        import gcp
        GOOGLE_APPLICATION_CREDENTIALS = gcp.detect_credentials_file()
        if GOOGLE_APPLICATION_CREDENTIALS:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = \
                GOOGLE_APPLICATION_CREDENTIALS
    return GOOGLE_APPLICATION_CREDENTIALS

GOOGLE_APPLICATION_CREDENTIALS = LazySetting(
    "GOOGLE_APPLICATION_CREDENTIALS", not_secret=True,
    getter=__GOOGLE_APPLICATION_CREDENTIALS, thread_safe=True)

GOOGLE_BIGQUERY_CTE = LazySetting(
    "GOOGLE_BIGQUERY_CTE", default="database/cte", local_only=SKIP_GCP,
    not_secret=True, thread_safe=True)

GOOGLE_BIGQUERY_DATASET = LazySetting(
    "GOOGLE_BIGQUERY_DATASET", default=CKBASE, local_only=SKIP_GCP,
    not_secret=True, thread_safe=True)

GOOGLE_BIGQUERY_DEFINITIONS = LazySetting(
    "GOOGLE_BIGQUERY_DEFINITIONS", default="database/definitions",
    local_only=SKIP_GCP, not_secret=True, thread_safe=True)

GOOGLE_BIGQUERY_QUERIES = LazySetting(
    "GOOGLE_BIGQUERY_QUERIES", default="database/queries", local_only=SKIP_GCP,
    not_secret=True, thread_safe=True)

GOOGLE_CLIENT_ID = LazySetting(
    "GOOGLE_CLIENT_ID",
    default="1000581300435-rg4jjufdr951imm5soiahi861cfu71en.apps.googleusercontent.com", thread_safe=True)

# used for signed URLs and any other signBlob/signJwt operations
GOOGLE_SIGNING_CREDENTIALS = LazySetting(
    "GOOGLE_SIGNING_CREDENTIALS",
    default="1000581300435-compute@developer.gserviceaccount.com",
    local_only=SKIP_GCP, thread_safe=True)

def __GOOGLE_STORAGE_BUCKET():
    """Getter for `GOOGLE_STORAGE_BUCKET` setting"""
    # try bucket name same as current project (e.g. `gpt-funhouse`)
    import gs
    GOOGLE_STORAGE_BUCKET = str(GOOGLE_CLOUD_PROJECT)
    if gs.bucket_exists(GOOGLE_STORAGE_BUCKET):
        return GOOGLE_STORAGE_BUCKET
    # try bucket name using CKBASE (e.g. `ckdev_bucket`)
    GOOGLE_STORAGE_BUCKET = str(GOOGLE_CLOUD_PROJECT)
    if gs.bucket_exists(CKBASE + "_bucket"):
        return GOOGLE_STORAGE_BUCKET
    raise ValueError("Could not find a Google Storage bucket to use")

GOOGLE_STORAGE_BUCKET = LazySetting(
    "GOOGLE_STORAGE_BUCKET", local_only=SKIP_GCP,
    getter=__GOOGLE_STORAGE_BUCKET, not_secret=True, thread_safe=True)

GOOGLE_STORAGE_FOLDER = LazySetting(
    "GOOGLE_STORAGE_FOLDER", default=CKBASE+"_corpus/temp/input/",
    local_only=SKIP_GCP, not_secret=True, thread_safe=True)

# used for Google Search API
GOOGLE_API_KEY = LazySetting("GOOGLE_API_KEY", thread_safe=True)

# used for Google Search API
GOOGLE_CSE_ID = LazySetting("GOOGLE_CSE_ID", thread_safe=True)

# also used for BigQuery datasets
GOOGLE_COMPUTE_REGION = LazySetting(
    "GOOGLE_COMPUTE_REGION", default="us-central1", not_secret=True,
    thread_safe=True)

GOOGLE_PUBSUB_TOPIC = LazySetting(
    "GOOGLE_PUBSUB_TOPIC", default="prediction_topic",
    local_only=SKIP_GCP, not_secret=True, thread_safe=True)

#
# APP SETTINGS
#

GUNICORN_TIMEOUT = LazySetting(
    "GUNICORN_TIMEOUT", default="300", not_secret=True, local_only=True,
    thread_safe=True)

GUNICORN_WORKER_CLASS = LazySetting(
    "GUNICORN_WORKER_CLASS", default="sync", not_secret=True, local_only=True,
    thread_safe=True)

GUNICORN_WORKERS = LazySetting(
    "GUNICORN_WORKERS", default="0", not_secret=True, local_only=True,
    thread_safe=True)

HTML_TEMPLATE = LazySetting(
    "HTML_TEMPLATE", default="bootstrap5.html", not_secret=True,
    local_only=True, thread_safe=True)

HTTPS_REDIRECT = LazySetting(
    "HTTPS_REDIRECT", default="false", not_secret=True, local_only=True,
    thread_safe=True)

# NOTE: NOT enforced for PUT requests using signed URLs in Google Cloud Storage
MAX_CONTENT_MB = LazySetting(
    "MAX_CONTENT_MB", default="50", not_secret=True, local_only=True,
    thread_safe=True)


# REDIRECT_URL = None
# if '.cloudshell.dev' in os.getenv('WEB_HOST', ''):
#     REDIRECT_URL = "https://5000-cs-576630579345-default.cs-us-west1-ijlt.cloudshell.dev/login"
#     print("REDIRECT_URL: " + REDIRECT_URL)


TMPDIR = LazySetting("TMPDIR", default="/tmp", local_only=True, not_secret=True)


def get_setting(setting_id, project_id=GOOGLE_CLOUD_PROJECT, default=None,
                prefix=SECRET_PREFIX, local_only=None, not_secret=False):
    """Get a setting from GCP Secret Manager or from the environment.
    :param setting_id: The ID of the secret to get.
    :param project_id: The ID of the project to get the secret from.
    :param default: The default value to return if the secret is not found.
    :param prefix: The prefix to add to the secret ID.
    :param local_only: If `True`, only look for the secret in the environment.
    :param not_secret: If `True`, log the value of the setting.
    :return: Setting string or exception is raised if not found.
    """
    import gcp

    logger.debug("[get_setting] %s (project_id=%s, default=%s, prefix=%s)",
                 setting_id, project_id, repr(default), prefix)

    # verify `secret_id` is a validate identifier
    assert setting_id.isidentifier(), f"Invalid secret ID: {setting_id}"

    # add prefix to secret ID
    fq_setting_id = prefix + setting_id if prefix else setting_id

    # allow for local override
    if os.getenv(fq_setting_id):
        if not_secret:
            logger.debug("[get_setting] %s found in environment: %s",
                         fq_setting_id, repr(os.environ[fq_setting_id]))
        return os.getenv(fq_setting_id)
    if os.getenv(setting_id):
        if not_secret:
            logger.debug("[get_setting] %s found in environment: %s",
                         setting_id, repr(os.environ[setting_id]))
        return os.getenv(setting_id)

    if local_only is None:
        local_only = SKIP_GCP

    if local_only:
        if default is not None:
            return default
        raise ValueError(f"Setting {setting_id} not found in environment.")

    if fq_setting_id not in gcp.get_secret_names(project_id):
        if default is not None:
            return default

    secret_value = gcp.get_secret(fq_setting_id, project_id=project_id)
    if not not_secret:
        logger.debug("[get_setting] %s found in Secret Manager: %s",
                     fq_setting_id, repr(secret_value))
    return secret_value
