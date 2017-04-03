import signal
import sys
import threading

import paho.mqtt.client as mqtt
import statsd
import yaml




class MQTTStat(threading.Thread):

    def __init__(self, hostname, topic, statsd_topic, statsd_type,
                 statsd_client, port=1883, websocket=False, client_id=None,
                 keepalive=60, will=None, auth=None, tls=None, qos=0):
        self.hostname = hostname
        self.port = port
        self.client_id = client_id
        self.keepalive = keepalive
        self.will = will
        self.auth = auth
        self.tls = tls
        self.qos = qos
        transport = "tcp"
        if websocket:
            transport = "websocket"
        self.statsd_client = statsd_client
        self.statsd_topic = statsd_topic
        self.statsd_method = statsd_type
        
        def on_message(client, userdata, msg):
            if statsd_type == 'gauge':
                statsd_client.gauge(statsd_topic, msg.payload)
            elif statsd_type == 'timer':
                statsd_client.timer(statsd_topic, msg.payload)
            elif statsd_type == 'counter':
                statsd_client.incr(statsd_topic)

        self.client = mqtt.Client(client=self.client_id, transport=transport)
        if tls:
            self.client.tls_set(**tls)
        if auth:
            self.client.username_pw_set(auth['username'],
                                        password=auth.get('password'))
        self.client.on_message = on_message
        self.client.connect(self.hostname, self.port, self.keepalive)
        self.client.subscribe(topic)

    def run(self):
        self.client.loop_forever()


def main():
    conf = None
    with open(sys.argv[1], 'r') as conf_file:
        conf = yaml.load(conf_file.read())
    if not conf:
        print('Unable to read yaml config file %s' % str(sys.argv[1]))
        sys.exit(1)

    # Read statsd config
    if 'statsd' not in conf:
        print('No statsd section found in specified config file')
        sys.exit(2)

    statsd_host = conf['statsd'].get('hostname')
    if not statsd_host:
        print('No valid statsd hostname provided in config file')
        sys.exit(2)
    statsd_port = conf['statsd'].get('port', 8125)
    if not statsd_port:
        print('No valid statsd port provided in config file')
    statsd_prefix = conf['statsd'].get('prefix', 'mosquitto.stats')
    statsd_client = statsd.StatsClient(host=statsd_host, port=statsd_port,
                                       prefix=statsd_prefix)
    # Read MQTT config
    if 'mqtt' not in conf:
        print('No MQTT section found in the specified config file')
        sys.exit(2)
    mqtt_hostname = conf['mqtt'].get('hostname')
    if not mqtt_hostname:
        print('No valid mqtt hostname provided in the config file')
        sys.exit(2)
    mqtt_port = conf['mqtt'].get('port', 1883)
    mqtt_keepalive = conf['mqtt'].get('keepalive', 60)
    # Configure MQTT auth
    auth = None
    username = conf['mqtt'].get('username')
    if username:
        auth = {'username': username}
    password = conf['mqtt'].get('password')
    if password and auth:
        auth['password'] = password
    # Max QOS
    mqtt_qos = conf['mqtt'].get('qos', 0)
    # Use websockets
    websocket = conf['mqtt'].get('websocket', False)
    # TLS configuration
    ca_certs = conf['mqtt'].get('ca_certs')
    certfile = conf['mqtt'].get('certfile')
    keyfile = conf['mqtt'].get('keyfile')
    tls = None
    if ca_certs is not None:
        tls = {'ca_certs': ca_certs, 'certfile': certfile,
               'keyfile': keyfile} 

    # Listen to topics and start statsd reporters
    if 'topics' not in conf:
        print('No topics specified in the config file')
        sys.exit(2)

    for topic in conf['topics']:
        statsd_topic = conf['topics'][topic].get('statsd_topic')
        if not statsd_topic:
            print('No statsd topic specified for mqtt topic %s' % topic)
            sys.exit(3)
        statsd_type = conf['topics'][topic].get('statsd_type', 'gague')
        if statsd_type not in ['gauge', 'counter', 'timer']:
            print('statsd_type %s on topic %s is not a valid type' % (
                statsd_type, topic))
        thread = MQTTStat(mqtt_hostname, topic, statsd_topic, statsd_type,
                          mqtt_port, websocket=websocket, auth=auth,
                          tls=tls, keepalive=mqtt_keepalive, qos=mqtt_qos)
        thread.start()

    while True:
        signal.pause()

if __name__ == "__main__":
    main()
