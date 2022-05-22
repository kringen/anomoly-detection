import pika
import atexit
import sys
import os
import logging
import yaml
import redis

logging.basicConfig(stream=sys.stdout, format='%(asctime)s %(levelname)-7s ' +
            '%(threadName)-15s %(message)s', level=logging.INFO)
r = redis.Redis(host='localhost', port=6379)
rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))

# Get configs from file-
cwd = os.path.dirname(__file__)
config_file = os.path.join(cwd,"config.yaml")
with open(config_file, "r") as configfile:
            config = yaml.safe_load(configfile)

def generateCallback(q):
    def callback(ch, method, properties, body):
        logging.info("received:{}, {}".format(queue,body))
        key = "readings:ethos:{}".format(q)
        r.rpush(key,body)

    return callback
#def callback(ch, method, properties, body):
#    logging.info("received:{}, {}, {}, {}".format(ch, method, properties,body))
#    key = "database:table:{}".format("test")
#    r.rpush(key,body)

def consume():
    channel = rabbitmq_connection.channel()

    for q in config["rabbitmq"]["queues"]:
        channel.queue_declare(queue=q)
        callback = generateCallback(q)
        channel.basic_consume(queue=q, on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
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