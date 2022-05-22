import logging
import sys
import lightstreamer as ls
import multiprocessing
import yaml
import os
import pika
import atexit
import time
import datetime

logging.basicConfig(stream=sys.stdout, format='%(asctime)s %(levelname)-7s ' +
            '%(threadName)-15s %(message)s', level=logging.INFO)
cwd = os.path.dirname(__file__)
config_file = os.path.join(cwd,"config.yaml")


class TelemetryReceiver:
    def __init__(self):
        self.readings_received = 0
        self.last_received = datetime.datetime.now().isoformat()

        with open(config_file, "r") as configfile:
            self.config = yaml.safe_load(configfile)
        # Connect to rabbitmq channel
        self.rabbitmq_server = self.config["rabbitmq"]["server"]
        self.rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters(self.rabbitmq_server))
        self.rabbitmq_channel = self.rabbitmq_connection.channel()
        # Loop through the rabbitmq.queues and declare a queue
        for q in self.config["rabbitmq"]["queues"]:
            self.rabbitmq_channel.queue_declare(queue=q)

    def receive_reading(self, reading):
        # Reading should be in this format:
        # {'pos': 1, 'name': 'NODE3000011', 'values': {'Value': '6.0327787399292'}}
        print(reading)
        queue = reading["name"]
        reading_value = reading["values"]["Value"]
        logging.debug("Queue: {}, Value: {}".format(queue, reading_value))
        # Publish to the queue
        self.rabbitmq_channel.basic_publish(exchange='',
                      routing_key=queue,
                      body=reading_value)

if __name__ == "__main__":
    tr = TelemetryReceiver()

    def cleanup():
        # Close rabbitmq connection
        logging.info("Closing connection to rabbitmq.")
        tr.rabbitmq_connection.close()
        # Unsubscribing from Lightstreamer by using the subscription key
        lightstreamer_client.unsubscribe(sub_key)
        # Disconnecting
        lightstreamer_client.disconnect()

    atexit.register(cleanup)

    # Establishing a new connection to Lightstreamer Server
    logging.info("Starting connection")
    lightstreamer_client = ls.LSClient("http://push.lightstreamer.com", "ISSLIVE")
    try:
        lightstreamer_client.connect()
    except Exception as e:
        logging.error("Unable to connect to Lightstreamer Server")
        logging.error(traceback.format_exc())
        sys.exit(1)
    # Get configurations
    with open(config_file, "r") as configfile:
        config = yaml.safe_load(configfile)
    # Making a new Subscription in MERGE mode
    subscription = ls.Subscription(
        mode="MERGE",
        items=config["rabbitmq"]["queues"],
        fields=["Value","TimeStamp","Status","Symbol"])
        #fields=["Value"])


    # A simple function acting as a Subscription listener
    def on_item_update(item_update):
        #print(item_update)
        tr.receive_reading(item_update)
        tr.last_received = datetime.datetime.now().isoformat()
        tr.readings_received += 1
    # Adding the "on_item_update" function to Subscription
    subscription.addlistener(on_item_update)
    # Registering the Subscription
    sub_key = lightstreamer_client.subscribe(subscription)

    while True:
        logging.info("Received {} readings as of {}".format(tr.readings_received, tr.last_received))
        time.sleep(30)
