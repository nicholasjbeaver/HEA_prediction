# import standard modules
import logging
import sys
import json
import os

# import 3rd party modules

# import local modules
from settings import (
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_COMPUTE_REGION,
    GOOGLE_PUBSUB_TOPIC,
    logger
)

# import common modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # add parent directory
import pubsub

# set the logging level to always be DEBUG in this module
logging.getLogger().setLevel(logging.INFO)

# TODO:
# 1. set subscription timeout so it will go away if not used
# 2. use keep alive if the client is still in scope...(goog for long running jobs)
# 3. decide on UOW so will know when to ack
# 4. test passing in a topic to use
# 5. test different status codes including failure and success
# 6. test multiple clients hitting just one server instance


if __name__ == "__main__":

    publish_topic = GOOGLE_PUBSUB_TOPIC

    # create a dictionary that includes key, corpus_id and type
    data = {"key": "value"}

    
    data = json.dumps(data).encode('utf-8')
    logging.info(f"message to publish: {data}")

    # Define your data and attributes.  These are optional and only used for filtering messages.
    attributes = {}

    pub_topic_id = publish_topic
    sub_topic_id = publish_topic  # will read from the same topic as published  

    logging.info(f"Creating a subscription for topic: {sub_topic_id}")
    subscription_id = pubsub.subscription(topic_id=sub_topic_id, subscription_id="testing_sub", **attributes)

    logging.debug(f'Created a subscription: {subscription_id}')
    pubsub.delete_when_done(name=subscription_id)

    # Publish the message
    logging.debug(f"Publish the message: {data} on topic {pub_topic_id}")
    pubsub.publish(data, topic_id=pub_topic_id, **attributes)

    # loop until receiving a signal to exit.
    try:
        while True:
            # Pull the message
            logging.debug(f"Pull messages: on {pub_topic_id} using subscription {subscription_id}")
            messages = pubsub.pull(topic_id=sub_topic_id, subscription_id=subscription_id)

            # Print the messages
            for message in messages:
                print(message.text, message.attributes)

    except KeyboardInterrupt:
        logging.info(f'keyboard interrupt received...exiting')

    # delete the subscription
    logging.info(f'deleting subscription: {subscription_id}')
    pubsub.delete(name=subscription_id)

    sys.exit(0)


