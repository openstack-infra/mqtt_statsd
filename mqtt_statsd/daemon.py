# Copyright 2017 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

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
        super(MQTTStat, self).__init__()
        self.hostname = hostname
        self.port = port
        self.client_id = client_id
        self.keepalive = keepalive
        self.mqtt_topic = topic
        self.will = will
        self.auth = auth
        self.tls = tls
        self.qos = qos
        transport = "tcp"
        if websocket:
            transport = "websocket"
        self.statsd_client = statsd_client
        self.statsd_topic = statsd_topic
        self.statsd_type = statsd_type
        self.client = mqtt.Client(transport=transport)
        if tls:
            self.client.tls_set(**tls)
        if auth:
            self.client.username_pw_set(auth['username'],
                                        password=auth.get('password'))

    def run(self):
        def on_connect(client, userdata, flags, rc):
            client.subscribe(self.mqtt_topic)

        def on_message(client, userdata, msg):
            if self.statsd_type == 'gauge':
                self.statsd_client.gauge(self.statsd_topic, msg.payload)
            elif self.statsd_type == 'timer':
                self.statsd_client.timer(self.statsd_topic, msg.payload)
            elif self.statsd_type == 'counter':
                self.statsd_client.incr(self.statsd_topic)

        self.client.on_connect = on_connect
        self.client.on_message = on_message
        self.client.connect(self.hostname, self.port)
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
        mqtt_topic = topic.get('mqtt_topic')
        if not mqtt_topic:
            print("No mqtt_topic specified for an entry in topics list")
            sys.exit(3)
        statsd_topic = topic.get('statsd_topic')
        if not statsd_topic:
            print('No statsd topic specified for mqtt topic %s' % mqtt_topic)
            sys.exit(3)
        statsd_type = topic.get('statsd_type', 'gauge')
        if statsd_type not in ['gauge', 'counter', 'timer']:
            print('statsd_type %s on topic %s is not a valid type' % (
                statsd_type, mqtt_topic))
        thread = MQTTStat(mqtt_hostname, mqtt_topic, statsd_topic, statsd_type,
                          statsd_client, mqtt_port, websocket=websocket,
                          auth=auth, tls=tls, keepalive=mqtt_keepalive,
                          qos=mqtt_qos)
        thread.start()

    while True:
        signal.pause()

if __name__ == "__main__":
    main()
