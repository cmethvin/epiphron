from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError
import json


def listen(project_id, subscription_id, callback):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

    with subscriber:
        try:
            streaming_pull_future.result()
        except TimeoutError:
            streaming_pull_future.cancel()

    subscriber.close()


class ResultsPublisher:
    def __init__(self):
        self.client = pubsub_v1.PublisherClient()

    def publish(self, project_id, topic_id, data):
        topic = f'projects/{project_id}/topics/{topic_id}'
        json_data = json.dumps(data)

        def callback(future):
            message_id = future.result()
            print(f'Successfully published message {message_id}')

        future = self.client.publish(topic, json_data.encode())
        future.add_done_callback(callback)