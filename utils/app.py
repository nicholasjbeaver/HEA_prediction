# import standard libraries
import logging
import base64

# import 3rd party libraries
from flask import Flask, request
from dotenv import load_dotenv
load_dotenv()

# import local modules
import ingestion_pipeline.pubsub_config as psc
from ingestion_pipeline.ingestion_router import process_message

# create a cloud run server to read a message from Google pubsub
# and log the message using the logging module
# https://cloud.google.com/run/docs/quickstarts/build-and-deploy/python

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


@app.route("/", methods=["POST"])
def index():
    envelope = request.get_json()
    if not envelope:
        msg = "no Pub/Sub message received"
        logging.error(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    if not isinstance(envelope, dict) or "message" not in envelope:
        msg = "invalid Pub/Sub message format"
        logging.error(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    pubsub_message = envelope["message"]

    message = "<no message>"
    attributes = {}
    if isinstance(pubsub_message, dict) and "data" in pubsub_message:
        message = base64.b64decode(pubsub_message["data"]).decode("utf-8").strip()
        attributes = pubsub_message["attributes"]

    logging.info(f"Message received from pubsub: {message} with attributes: {attributes}")

    # process the message
    try:
        process_message(message, attributes)
    except Exception as e:
        # catch all exceptions so we don't crash the server
        logging.error(f"Error {e} processing message: {message} with attributes: {attributes}")

    # During this return, the pubsub push will ack the message
    return "OK", 204  # 204 is a success with no content
