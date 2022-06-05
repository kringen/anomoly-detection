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

readings_count = 0

# Get configs from file
try:
    cwd = os.path.dirname(__file__)
    config_file = os.path.join(cwd,"config.yaml")
    with open(config_file, "r") as configfile:
            config = yaml.safe_load(configfile)
    logging.info("Read config file: {}".format(config))
except Exception as e:
    logging.error("Unable to load config.yaml")
    logging.error(traceback.format_exc())
    sys.exit(1)

# Connect to Redis Server
try:
    redis_server = config["redis"]["server"]
    r = redis.Redis(host=redis_server, port=6379)
    logging.info("Connected to {}".format(redis_server))
except Exception as e:
    logging.error("Unable to connect to Redis Server")
    logging.error(traceback.format_exc())
    sys.exit(1)

# Connect to Rabbitmq server
try:
    rabbitmq_server = config["rabbitmq"]["server"]
    rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_server))
    logging.info("Connected to {}".format(rabbitmq_server))
except Exception as e:
    logging.error("Unable to connect to Rabbitmq Server")
    logging.error(traceback.format_exc())
    sys.exit(1)

def generateCallback(q):
    def callback(ch, method, properties, body):
        logging.debug("received:{}, {}".format(q,body))
        stream = "readings:{}".format(q)
        r.xadd(stream, json.loads(body))
        readings_count += 1
        logging.info("Cumulative readings: {}".format(readings_count))
        # This will push to a stream named readings:ethos:<sensor>
        # To read from this stream:
        # XREAD STREAMS readings:ethos:NODE3000011 0-0
    return callback


def consume():
    channel = rabbitmq_connection.channel()

    try:
        # For each queue in config file, create a consumer and wait for messages
        for q in config["rabbitmq"]["queues"]:
            channel.queue_declare(queue=q)
            callback = generateCallback(q)
            channel.basic_consume(queue=q, on_message_callback=callback, auto_ack=True)
            logging.info("Consuming queue: {}".format(q))

        logging.info("Starting to consume messages...")
        channel.start_consuming()
    except Exception as e:
        logging.error("Unable to connect to subscribe to queues")
        logging.error(traceback.format_exc())
        sys.exit(1)

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
