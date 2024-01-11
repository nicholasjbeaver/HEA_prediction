# import standard modules
import logging
import sys
import json
import os

# import 3rd party modules

# import local modules
from gcp_utils.settings import (
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_COMPUTE_REGION,
    GOOGLE_PUBSUB_TOPIC,
    logger
)

from gcp_utils import pubsub

# set the logging level to always be DEBUG in this module
logger.setLevel(logging.INFO)

# TODO:


if __name__ == "__main__":

    publish_topic = GOOGLE_PUBSUB_TOPIC

    # create a dictionary that includes key, corpus_id and type
    data = {"key": "value"}

    
    data = json.dumps(data).encode('utf-8')
    logger.info(f"message to publish: {data}")

    # Define your data and attributes.  These are optional and only used for filtering messages.
    attributes = {}

    pub_topic_id = publish_topic
    sub_topic_id = publish_topic  # will read from the same topic as published  

    logger.info(f"Creating a subscription for topic: {sub_topic_id}")
    subscription_id = pubsub.subscription(topic_id=sub_topic_id, subscription_id="testing_sub", **attributes)

    loggier.debug(f'Created a subscription: {subscription_id}')
    pubsub.delete_when_done(name=subscription_id)

    # Publish the message
    logger.debug(f"Publish the message: {data} on topic {pub_topic_id}")
    pubsub.publish(data, topic_id=pub_topic_id, **attributes)

    # loop until receiving a signal to exit.
    try:
        while True:
            # Pull the message
            logger.debug(f"Pull messages: on {pub_topic_id} using subscription {subscription_id}")
            messages = pubsub.pull(topic_id=sub_topic_id, subscription_id=subscription_id)

            # Print the messages
            for message in messages:
                print(message.text, message.attributes)

    except KeyboardInterrupt:
        logger.info(f'keyboard interrupt received...exiting')

    # delete the subscription
    logger.info(f'deleting subscription: {subscription_id}')
    pubsub.delete(name=subscription_id)

    sys.exit(0)


