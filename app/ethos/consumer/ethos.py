import pika
import atexit
import sys
import os
import logging
import yaml
import redis
import json
import datetime

logging.basicConfig(stream=sys.stdout, format='%(asctime)s %(levelname)-7s ' +
            '%(threadName)-15s %(message)s', level=logging.INFO)

# Get configs from file-
cwd = os.path.dirname(__file__)
config_file = os.path.join(cwd,"config.yaml")
with open(config_file, "r") as configfile:
            config = yaml.safe_load(configfile)

redis_server = config["redis"]["server"]
r = redis.Redis(host=redis_server, port=6379)
rabbitmq_server = config["rabbitmq"]["server"]
rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters(host=redis_server))

def generateCallback(q):
    def callback(ch, method, properties, body):
        logging.debug("received:{}, {}".format(q,body))
        stream = "readings:ethos:{}".format(q)
        r.xadd(stream, json.loads(body))
        # This will push to a stream named readings:ethos:<sensor>
        # To read from this stream:
        # XREAD STREAMS readings:ethos:NODE3000011 0-0
    return callback


def consume():
    channel = rabbitmq_connection.channel()

    # For each queue in config file, create a consumer and wait for messages
    for q in config["rabbitmq"]["queues"]:
        channel.queue_declare(queue=q)
        callback = generateCallback(q)
        channel.basic_consume(queue=q, on_message_callback=callback, auto_ack=True)

    logging.info("Starting to consume messages...")
    channel.start_consuming()

def cleanup():
    # Close rabbitmq connection
    logging.info("Closing connection to rabbitmq.")
    rabbitmq_connection.close()

if __name__ == '__main__':
    atexit.register(cleanup)
    try:
        consume()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
