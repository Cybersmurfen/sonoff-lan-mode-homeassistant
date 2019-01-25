#!/usr/bin/env python3

# This script can be used to simulate a real Sonoff device in LAN mode, to test 2-way communication with other code.
# When executed (e.g. from a terminal with `python mock_sonoff.py`), it will open a WebSocket server on port 8081,
# allowing you to connect to this mock Sonoff device with other code designed to simulate the eWeLink mobile app.
# Any messages sent or received are logged to the log file 'mock_sonoff.log' for further research.

LOG_LEVEL = "INFO"
MULTI_OUTLET = True
MOMENTARY = True

import json
import logging
import logging.config
import threading
import time
from websocket_server import WebsocketServer


class MockSonoff:
    def __init__(self):
        self.logger = self.configure_logger('default', 'mock_sonoff.log')
        self.logger.debug('MockSonoff class initialising')

        self.server = None
        websocket_thread = threading.Thread(target=self.init_websocket(self.logger))
        websocket_thread.daemon = True
        websocket_thread.start()

        while True:
            time.sleep(1)

    def init_websocket(self, logger):
        self.logger = logger
        self.logger.info('Running websocket server on localhost port 8081 to simulate Sonoff')

        self.server = WebsocketServer(8081, '127.0.0.1', logging.ERROR)
        self.server.set_fn_new_client(self.new_client)
        self.server.set_fn_client_left(self.client_left)
        self.server.set_fn_message_received(self.on_message)
        self.server.run_forever()

    def new_client(self, client, server):
        self.logger.debug("New client connected and was given id %d" % client['id'])

    def client_left(self, client, server):
        self.logger.debug("Client(%d) disconnected" % client['id'])

    def on_message(self, client, server, data):
        self.logger.debug('Received websocket msg: %s' % data)

        data = json.loads(data)
        self.logger.debug('Action: %s' % data['action'])

        if 'action' in data and data['action'] == 'userOnline':
            self.logger.info('Received userOnline action, sending simulated hello response')
            self.server.send_message_to_all(json.dumps({
                "error": 0,
                "apikey": "09a15816-c289-4333-bf7b-aa52ffafdf96",
                "sequence": "1548124045842",
                "deviceid": "100060af40"
            }))

            self.logger.info('Waiting 1 second, then sending simulated initial switch state')
            time.sleep(1)

            if MULTI_OUTLET:
                self.server.send_message_to_all(json.dumps({
                    "userAgent": "device",
                    "apikey": "nonce",
                    "deviceid": "100060af40",
                    "action": "update",
                    "params": {
                        "switches": [{"switch": "off", "outlet": 0}, {"switch": "off", "outlet": 1},
                                     {"switch": "off", "outlet": 2}, {"switch": "off", "outlet": 3}]
                    }
                }))
            else:
                self.server.send_message_to_all(json.dumps({
                    "userAgent": "device",
                    "apikey": "09a15816-c289-4333-bf7b-aa52ffafdf96",
                    "deviceid": "100060af40",
                    "action": "update",
                    "params": {
                        "switch": "off"
                    }
                }))

            self.logger.info('Now waiting 10 seconds before simulating manual switch ON')
            time.sleep(10)

            if MULTI_OUTLET:
                self.logger.info("Sending Outlet 1 ON message to client %d" % client['id'])
                self.server.send_message_to_all(json.dumps({
                    "userAgent": "device",
                    "apikey": "apikey",
                    "deviceid": "100040e943",
                    "action": "update",
                    "params": {
                        "switches": [
                            {"switch": "on", "outlet": 1}
                        ]
                    }
                }))

                if MOMENTARY:
                    self.logger.info("Waiting 1 second, then sending Outlet 1 OFF message for momentary switch")
                    time.sleep(1)

                    self.server.send_message_to_all(json.dumps({
                        "userAgent": "device",
                        "apikey": "apikey",
                        "deviceid": "100040e943",
                        "action": "update",
                        "params": {
                            "switches": [
                                {"switch": "off", "outlet": 1}
                            ]
                        }
                    }))

            else:
                self.logger.info("Sending switch ON message to client %d" % client['id'])
                self.server.send_message_to_all(json.dumps({
                    "userAgent": "device",
                    "apikey": "09a15816-c289-4333-bf7b-aa52ffafdf96",
                    "deviceid": "100060af40",
                    "action": "update",
                    "params": {
                        "switch": "on"
                    }
                }))

    def configure_logger(self, name, log_path):
        # Fix for duplicate log entries caused by basic config initialisation inside websocket-server module
        default_logger = logging.getLogger()
        default_logger.handlers = []

        logging.config.dictConfig({
            'version': 1,
            'formatters': {
                'default': {'format': '%(asctime)s - %(levelname)s - %(message)s', 'datefmt': '%Y-%m-%d %H:%M:%S'}
            },
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    'formatter': 'default',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'level': 'DEBUG',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'formatter': 'default',
                    'filename': log_path,
                    'maxBytes': 10000,
                    'backupCount': 3
                }
            },
            'loggers': {
                'default': {
                    'level': LOG_LEVEL,
                    'handlers': ['console', 'file']
                }
            },
            'disable_existing_loggers': True
        })
        return logging.getLogger(name)


if __name__ == '__main__':
    MockSonoff()