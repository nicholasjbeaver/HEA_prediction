"""Pub/Sub Helpers"""
# Standard imports
from collections import namedtuple
from contextlib import contextmanager
import hashlib
import json
import queue
import time

# Third-party imports

# Local imports
import gcp
from settings import (
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_COMPUTE_REGION,
    GOOGLE_PUBSUB_TOPIC,
    logger
)
from utils import (
    duck_bytes,
)


# simplified immutable type to represent a Pub/Sub message
PubSubMessage = namedtuple(
    "PubSubMessage",
    ["text", "attributes", "publish_time", "data"])


class Publishable:
    """Callable instance for publishing data to topic"""
    def __init__(self, topic_id=GOOGLE_PUBSUB_TOPIC,
                 project_id=GOOGLE_CLOUD_PROJECT,
                 **default_attributes):
        self.publisher = _publisher()
        self.topic_path = self.publisher.topic_path(
            str(project_id), str(topic_id))
        self.default_attributes = default_attributes.copy()

    def __call__(self, data, **attributes):
        data = duck_bytes(data)

        # start with default_attributes and then add attributes
        publisher_attributes = self.default_attributes.copy()
        publisher_attributes.update({k: str(v) for k, v in attributes.items()})

        # `ordering_key` is a tag for grouping messages together and Pub/Sub
        # uses it to ensure delivery is in same the order as when published
        # (see https://cloud.google.com/pubsub/docs/ordering)
        ordering_key = publisher_attributes.pop('ordering_key', None)

        # if none is provided then use a hash of all the `*_id` attributes
        if ordering_key is None:
            id_keys_sorted = sorted([k for k in publisher_attributes.keys()
                                        if k.endswith('_id')])
            id_values = [publisher_attributes[k] for k in id_keys_sorted]
            ordering_key = hashlib.sha256(
                ''.join(id_values).encode('utf-8')).hexdigest()
            logger.debug("[pubsub] ORDERING: %s %s",
                         ordering_key, id_keys_sorted)
        else:
            logger.debug("[pubsub] ORDERING: %s (specific)",
                         ordering_key)

        logger.debug("[pubsub] PUBLISH: %s %s",
                     data, repr(publisher_attributes))

        return self.publisher.publish(
            self.topic_path,
            data=data,
            ordering_key=ordering_key,
            **publisher_attributes)


def _message(message):
    """Construct immutable Pub/Sub message from message object"""

    # attempt to decode message data as utf-8
    try:
        text = message.data.decode('utf-8')
    except UnicodeDecodeError:
        text = None

    return PubSubMessage(
        text=text,
        attributes=dict(message.attributes).copy(),
        publish_time=message.publish_time,
        data=message.data,
    )


def _publisher(region=GOOGLE_COMPUTE_REGION):
    """Return Pub/Sub client for Publisher"""
    from google.cloud import pubsub_v1
    publisher_options = pubsub_v1.types.PublisherOptions(
        enable_message_ordering=True)
    # Sending to same region ensures order even with multiple publishers
    client_options = {
        "api_endpoint": f"{region}-pubsub.googleapis.com:443"
    }
    return pubsub_v1.PublisherClient(
        publisher_options=publisher_options,
        client_options=client_options,
        credentials=gcp.credentials())


def _subscriber():
    """Return Pub/Sub client for Subscriber"""
    from google.cloud import pubsub_v1
    return pubsub_v1.SubscriberClient(credentials=gcp.credentials())


def build_filter(**kwargs):
    """Build a subscription filter string based on the given kwargs.

    Example usage:
    build_filter(foo='bar', baz__gt=42)

    This will generate a filter string like:
    'foo="bar" AND baz>42'

    :param kwargs: keyword arguments representing filter conditions
    :return: subscription filter string
    """
    filter_parts = []
    for key, value in kwargs.items():
        assert key not in {'filter', 'project_id', 'topic_id', 'subscription_id'}
        if '__' in key:
            field, op = key.split('__')
        else:
            field, op = key, 'eq'

        field = f"attributes.{field}"

        if op == 'eq':
            filter_parts.append(f'{field}="{value}"')
        elif op == 'in':
            filter_parts.append(f'{field}:{value}')
        elif op == 'not':
            filter_parts.append(f'{field}!={value}')
        else:
            raise ValueError(f'Unsupported operator: {op}')

    filter = ' AND '.join(filter_parts)
    logger.debug(f"[pubsub] FILTER: %s", filter)
    return filter


def delete(name, project_id=GOOGLE_CLOUD_PROJECT):
    """Delete a topic or subscription by name
    :param name: Topic or subscription name
    :param project_id: Google Cloud project ID
    :return: True if deleted, False if not found"""
    from google.api_core.exceptions import NotFound
    publisher = None
    subscriber = None
    subscription_path = None
    topic_path = None
    deleted = False

    if "/subscriptions/" in name:
        subscriber = _subscriber()
        subscription_path = name
    elif "/topics/" in name:
        publisher = _publisher()
        topic_path = name
    else:  # try both starting with subscriptions
        subscriber = _subscriber()
        subscription_path = subscriber.subscription_path(str(project_id), name)
        publisher = _publisher()
        topic_path = publisher.topic_path(str(project_id), name)

    if subscriber:
        with subscriber:
            try:
                logger.debug("[pubsub] DELETE: %s", subscription_path)
                subscriber.delete_subscription(request={
                    "subscription": subscription_path})
                deleted = True
            except NotFound:
                logger.debug("[pubsub] NOT FOUND: %s", subscription_path)

    if publisher:
        with publisher:
            try:
                logger.debug("[pubsub] DELETE: %s", topic_path)
                publisher.delete_topic(request={"topic": topic_path})
                deleted = True
            except NotFound:
                logger.debug("[pubsub] NOT FOUND: %s", topic_path)

    return deleted


@contextmanager
def delete_when_done(name):
    """Delete the Pub/Sub resource when the context exits"""
    try:
        yield
    finally:
        delete(name)


def pull(topic_id=GOOGLE_PUBSUB_TOPIC, subscription_id=None,
         max_messages=100, timeout=5.0, leave_unacked=False, 
         project_id=GOOGLE_CLOUD_PROJECT, **filter_kwargs):
    """Pull new messages and return them with their attributes
    :param topic_id: Topic name
    :param subscription_id: Subscription name
    :param max_messages: Max messages to poll
    :param blocking: If True, block until messages are available
    :param project_id: Project name
    :param filter_kwargs: Keyword arguments to build a filter string
    :return: List of `PubSubMessage` (text, attributes, data)"""
    from google.api_core.exceptions import DeadlineExceeded

    subscriber = _subscriber()
    subscription_path = subscription(topic_id=topic_id,
                                     subscription_id=subscription_id,
                                     project_id=project_id,
                                     **filter_kwargs)

    try:
        response = subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": max_messages,
            },
            timeout=timeout,
        )
    except DeadlineExceeded:
        response = None

    received = []
    if response and response.received_messages:
        ack_ids = []
        for received_message in response.received_messages:
            logger.debug(f"[pubsub] PULL: %s (%s)", 
                         repr(received_message.message.data),
                         repr(received_message.message.attributes))
            if not leave_unacked:
                ack_ids.append(received_message.ack_id)
            received.append(_message(received_message.message))

        # ack messages if not leaving them unacked
        if ack_ids:
            subscriber.acknowledge(request={
                "subscription": subscription_path,
                "ack_ids": ack_ids,
            })

    return received


def publish(data, topic_id=GOOGLE_PUBSUB_TOPIC, project_id=GOOGLE_CLOUD_PROJECT,
            **attributes):
    """Publish data to topic"""
    return Publishable(topic_id, project_id=project_id)(data, **attributes)


def publishable(topic_id=GOOGLE_PUBSUB_TOPIC, project_id=GOOGLE_CLOUD_PROJECT,
                **default_attributes):
    """Return callable instance for publishing data to topic"""
    return Publishable(topic_id=topic_id, project_id=project_id,
                       **default_attributes)


def streaming_pull(topic_id=GOOGLE_PUBSUB_TOPIC, subscription_id=None,
                   max_messages=100, timeout=5.0, leave_unacked=False,
                   project_id=GOOGLE_CLOUD_PROJECT, **filter_kwargs):
    """Continually gather messages, ack & yield them
    :param topic_id: Topic name
    :param subscription_id: Subscription name
    :param max_messages: Max messages to gather in a batch
    :param timeout: Overall time to wait for messages
    :param leave_unacked: If True, leave messages unacked
    :param project_id: Project name
    :param filter_kwargs: Filter kwargs for subscription
    :return: Generator of `PubSubMessage` (text, attributes, data)"""
    from concurrent.futures import TimeoutError

    subscriber = _subscriber()
    subscription_path = subscription(topic_id=topic_id,
                                     subscription_id=subscription_id,
                                     project_id=project_id,
                                     **filter_kwargs)
    message_ids = []
    message_queue = queue.Queue()
    start_time = time.time()

    def streaming_pull_callback(message):
        logger.debug(f"[pubsub] STREAM: %s (%s)",
                     repr(message.data), repr(message.attributes))
        if not leave_unacked:
            message.ack()
        message_ids.append(message.message_id)
        message_queue.put(_message(message))

    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=streaming_pull_callback)
 
    with subscriber:
        try:
            while len(message_ids) < max_messages:
                elapsed_seconds = time.time() - start_time
                if elapsed_seconds >= timeout:
                    break
                interval_timeout = max(timeout - elapsed_seconds, 0.1)
                logger.debug("[streaming_pull] %.2f elapsed, waiting %.2f",
                             elapsed_seconds, interval_timeout)
                yield message_queue.get(timeout=interval_timeout)

        except (queue.Empty, TimeoutError):
            streaming_pull_future.cancel()

        streaming_pull_future.result()

    elapsed_seconds = time.time() - start_time

    logger.debug("[pubsub] STREAMED: %d msg %.2f sec",
                 len(message_ids), elapsed_seconds)


def subscription(topic_id=GOOGLE_PUBSUB_TOPIC, subscription_id=None,
                 unordered=None, project_id=GOOGLE_CLOUD_PROJECT,
                 **filter_kwargs):
    """Create a subscription to a topic with optional filtering
    :param topic_id: Topic name
    :param subscription_id: Subscription name
    :param unordered: If True, disable message ordering (for create only)
    :param project_id: Project name
    :param filter_kwargs: Filter arguments"""
    from google.api_core.exceptions import NotFound

    subscriber = _subscriber()
    filter = build_filter(**filter_kwargs)

    # auto-determine subscription name if not provided
    if not subscription_id:
        if filter:
            subscription_id = hashlib.sha256(
                filter.encode("utf-8")).hexdigest()
        else:
            subscription_id = "sub"

    # if subscription_id is already fully qualified then use that as-is
    if subscription_id.startswith("projects/"):
        subscription_path = subscription_id
    else:
        # subscription name MUST start with topic name
        if not str(subscription_id).startswith(str(topic_id)):
            subscription_id = f"{topic_id}-{subscription_id}"

        # generate subscription path
        subscription_path = subscriber.subscription_path(
            str(project_id), str(subscription_id))

    # verify subscription exists or create it if it doesn't
    with subscriber:
        try:
            result = subscriber.get_subscription(request={
                "subscription": subscription_path,
            })
        except NotFound:
            topic_path = _publisher().topic_path(str(project_id), str(topic_id))
            result = subscriber.create_subscription(request={
                "name": subscription_path,
                "topic": topic_path,
                "filter": filter,
                "enable_message_ordering": not unordered,
            })

    # verify the subscription has the same ordering as requested
    if unordered is not None:
        assert result.enable_message_ordering != unordered

    logger.debug("[pubsub] SUBSCRIPTION [%s|%s]: %s",
                 topic_id, filter, result.name)
    return result.name


@contextmanager
def subscription_context(**kwargs):
    """Context manager for creating a subscription and deleting it on exit
    :param kwargs: Keyword arguments for `subscription`"""
    subscription_path = subscription(**kwargs)
    try:
        yield subscription_path
    finally:
        delete(subscription_path)


def topic(topic_id=GOOGLE_PUBSUB_TOPIC, project_id=GOOGLE_CLOUD_PROJECT):
    """Get topic in project or create it if it doesn't exist
    :param topic_id: Topic name
    :param project_id: Project name
    """
    from google.api_core.exceptions import NotFound

    publisher = _publisher()

    # if topic_id is already fully qualified then use that as-is
    if str(topic_id).startswith("projects/"):
        topic_path = topic_id
    else:
        topic_path = publisher.topic_path(str(project_id), str(topic_id))

    try:
        _topic = publisher.get_topic(request={"topic": topic_path})
    except NotFound:
        _topic = publisher.create_topic(request={"name": topic_path})

    return topic_path


def topics(project_id=GOOGLE_CLOUD_PROJECT, fully_qualified=False):
    """List topics in project
    :param project_id: Project name
    :param fully_qualified: If True, return fully qualified topic names
    :return: Set of topic names"""
    publisher = _publisher()
    _topics = set()
    for topic_path in publisher.list_topics(
            request={"project":f"projects/{project_id}"}):
        if fully_qualified:
            _topics.add(topic_path.name)
        else:
            _topics.add(topic_path.name.split('/')[-1])
    return _topics
