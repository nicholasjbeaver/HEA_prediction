# This module contains configuration information for PubSub infrastructure.
import logging
import os


# set the default logging format and to only log errors.  logging level is overridden in each module if desired
logging.basicConfig(format='%(process)d: %(asctime)s: %(levelname)s: %(funcName)s: %(message)s', level=logging.ERROR)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# if this is running on a cloud machine, this variable should already be set
GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')

# For testing in the cloud  environment but on local machine
if GOOGLE_CLOUD_PROJECT is None:
    GOOGLE_CLOUD_PROJECT = 'phase-prediction'
    os.environ['GOOGLE_CLOUD_PROJECT'] = GOOGLE_CLOUD_PROJECT


# For testing in the cloud  environment but on local machine
GOOGLE_COMPUTE_REGION = os.environ.get('GOOGLE_COMPUTE_REGION')
if GOOGLE_COMPUTE_REGION is None:
    GOOGLE_COMPUTE_REGION = 'us-central1'
    os.environ['GOOGLE_COMPUTE_REGION'] = GOOGLE_COMPUTE_REGION


BUCKET = os.environ.get('BUCKET')  # get bucket name from GCP
if BUCKET is None:
    BUCKET = f'gs://{GOOGLE_CLOUD_PROJECT}'  # use the default project bucket

# PubSub topics and subscriptions
GOOGLE_PUBSUB_TOPIC = f"prediction_topic"
