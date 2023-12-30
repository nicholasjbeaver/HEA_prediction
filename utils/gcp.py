"""Google Cloud Platform (GCP) Helpers"""
# Standard imports
import configparser
import functools
import os
import re

# Local imports
from settings import (
    GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT,
    GOOGLE_SIGNING_CREDENTIALS,
    logger
)
from utils import duck_dict


def credentials(credentials_file=GOOGLE_APPLICATION_CREDENTIALS):
    """Return `credentials` (for use in `Client` constructors) based on file"""
    import google.auth
    _credentials = None
    if credentials_file is not None and str(credentials_file):
        _credentials, _ = google.auth.load_credentials_from_file(
            str(credentials_file))

    # attempt to determine credentials from compute engine metadata server
    # (works only when running on GCP compute engine, cloud run, etc.)
    if not _credentials:
        _credentials, _ = google.auth.default()

    return _credentials


@functools.cache
def detect_credentials_file():
    """Return full path to user's GCP credentials JSON or `None` if not found"""
    gcp_credentials_path = os.path.expanduser(
        "~/.config/gcloud/legacy_credentials/")
    if os.path.exists(gcp_credentials_path):
        for subdir in os.listdir(gcp_credentials_path):
            adc_path = os.path.join(gcp_credentials_path, subdir, "adc.json")
            if os.path.exists(adc_path):
                return adc_path
    return None


@functools.cache
def detect_project():
    import google.auth

    project_id = None
    gcloud_config_path = os.path.expanduser("~/.config/gcloud/configurations/config_default")

    if os.path.exists(gcloud_config_path):
        logger.debug("[get_default_project] Checking %s", gcloud_config_path)
        config = configparser.ConfigParser()
        config.read(gcloud_config_path)

        # Enumerate the sections in the config file.
        for section in config.sections():
            # If the section is "default" or "core", return the project ID.
            if section in ["default", "core"]:
                project_id = config[section]["project"]

    if project_id is None:
        logger.debug("[get_default_project] Trying google.auth.default()")
        _, project_id = google.auth.default()

    logger.debug("[get_default_project] project_id=%s", repr(project_id))
    return project_id


@functools.cache
def get_secret_names(project_id=GOOGLE_CLOUD_PROJECT):
    """Get a list of secret names for a project
    :param project_id: The ID of the project to get the secrets for.
    :return: Set of secret names"""
    from google.cloud import secretmanager

    logger.debug("[get_secret_names] Listing %s", project_id)
    client = secretmanager.SecretManagerServiceClient(credentials=credentials())
    secret_names = set()
    for secret in client.list_secrets(
            request={"parent": f"projects/{project_id}"}):
        secret_names.add(secret.name.split("/")[-1])
    # show all secrets (without project_id prefix)
    logger.debug("[get_secret_names] %s: %s", project_id, secret_names)
    return secret_names


@functools.cache
def get_secret(secret_id, default=None, project_id=GOOGLE_CLOUD_PROJECT):
    """Get a secret from GCP Secret Manager
    :param project_id: The ID of the project to get the secret from.
    :param secret_id: The ID of the secret to get.
    :return: Secret string or exception is raised if not found.
    """
    from google.cloud import secretmanager
    import google.api_core.exceptions

    logger.debug("[get_secret] %s/%s", project_id, secret_id)
    client = secretmanager.SecretManagerServiceClient(credentials=credentials())
    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    try:
        response = client.access_secret_version(request={"name": secret_name})
    except google.api_core.exceptions.NotFound:
        if default is not None:
            return default
        raise ValueError(f"Secret {secret_id} not found in {project_id}.")
    return response.payload.data.decode("UTF-8")


def impersonate(target_principal, target_scopes=None, expiration=3600):
    """Impersonate a service account
    :param target_principal: Email address of a service account to impersonate.
    :param target_scopes: List of scopes to request for authorization grant.
    :param expiration: Lifetime of impersonated credentials in seconds.
    :return: Impersonated credentials
    """
    from google.auth import impersonated_credentials

    if target_scopes is None:
        target_scopes = [
            "https://www.googleapis.com/auth/devstorage.read_write"
        ]

    # NOTE: The role roles/iam.serviceAccountTokenCreator must be granted to
    # the source credentials for this to work
    # https://cloud.google.com/iam/docs/service-account-permissions#token-creator-role

    return impersonated_credentials.Credentials(
        source_credentials=credentials(),
        target_principal=target_principal,
        target_scopes=target_scopes,
        lifetime=expiration)


def running_in_appengine():
    """Return `True` if running in App Engine."""
    return 'GAE_ENV' in os.environ


def signing_credentials(file_or_info=GOOGLE_SIGNING_CREDENTIALS):
    """Determine credentials for signing URLs
    :param file_or_info: Optional path to file or JSON / dictionary"""
    import google.auth
    from google.auth import compute_engine
    from google.auth.transport import requests
    from google.oauth2 import service_account

    # if an explicit value is provided, use it
    if file_or_info is not None:
        file_or_info = str(file_or_info)

    # if file_or_info matches basic email address REGEX then impersonate
    if not file_or_info:
        pass
    elif re.match(r"[^@]+@[^@]+\.[^@]+", file_or_info):
        logger.info("[signing_credentials] Impersonating %s", file_or_info)
        return impersonate(file_or_info)
    elif os.path.exists(file_or_info):
        logger.info("[signing_credentials] Loading %s", file_or_info)
        return google.auth.load_credentials_from_file(file_or_info)[0]
    elif file_or_info:
        logger.info("[signing_credentials] Parsing JSON/dict")
        return service_account.Credentials.from_service_account_info(
            duck_dict(file_or_info))

    # if no explicit value is provided, see if our default credentials are OK
    source_credentials = credentials()

    # service account has a private key which can be used for signing
    if isinstance(credentials, service_account.Credentials):
        logger.info("[signing_credentials] Using service account credentials")
        return source_credentials

    # NOTE: hack for signing when running on Google Compute Engine (GCE)
    # See: https://stackoverflow.com/questions/46540894
    if isinstance(source_credentials, compute_engine.credentials.Credentials):
        logger.info("[signing_credentials] Using GCE credentials")
        auth_request = requests.Request()
        source_credentials.refresh(auth_request)
        return compute_engine.IDTokenCredentials(
            auth_request,
            "",
            service_account_email=source_credentials.service_account_email
        )

    logger.warning("[signing_credentials] No signing credentials found")
    return None
