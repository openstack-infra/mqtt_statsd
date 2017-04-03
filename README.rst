===========
mqtt_statsd
===========

As the name implies this a script to publish MQTT metrics into statsd. It was
originally designed to handle metrics from the $SYS/ topics in the mosquitto
broker, but the framework is generic enough that any MQTT topic can be used.

Installation
------------

mqtt_statsd is available via pypi, so all you need to do is run::

  pip install -U mqtt_statsd

to get mqtt_statsd on your system. If you need to use a development version of
mqtt_statsd you can clone the repo and install it locally with::

  git clone https://github.com/mtreinish/mqtt_statsd.git && pip install -e mqtt_statsd

which will install mqtt_statsd in your python environment in editable mode for
local development.

Configuring mqtt_statsd
-----------------------

Before you run mqtt_statsd you have to create a yaml configuration file to tell
mqtt_statsd how to connect to both the MQTT broker, and statsd. As well as which
MQTT topics to subscribe to and how to populate statsd with the data it gets
from that MQTT topic. For example::

    statsd:
      hostname: localhost
      # port is optional, the default is shown
      port: 8125
      # prefix is optional, the default is shown
      prefix: mosquitto.stats
    mqtt:
      hostname: localhost
      # port is optional, the default is shown
      port: 1883
      # keepalive is optional, the default is shown
      keepalive: 60
      # username is optional, there is no default
      username: foo
      # password is optional, there is no default. If username isn't set this
      # is ignored
      password: PASS
      # qos is optional, the default is shown
      qos: 0
      # websocket is optional, it defaults to False
      websocket: True
    topics:
      # You can specify as many topics as you want, and mqtt_statsd will
      # listen to all of them
      - $SYS/broker/messages/publish/sent:
        statsd_topic: publish_messages_sent
        # statsd_type is optional, the default is shown. Valid options are
        # gague, counter, and timer
        statsd_type: gauge
      - $SYS/broker/clients/connected:
        statsd_topic: connected_clients

Running mqtt_statsd
-------------------

Aftering installing and configuring mqtt_statsd running it is incredibly
straightforward. Just call ``mqtt_statsd`` and it takes 1 mandatory argument,
the path to the yaml config file. For example::

  mqtt_statsd my_config_file.yaml
