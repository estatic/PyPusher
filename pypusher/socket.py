import pkg_resources
import logging
from threading import Thread
import json
import sys
import copy
import hashlib
import hmac

from pypusher.channels import Channels
from pypusher.channel import Channel
from pypusher.websocket import PusherWebSocket

VERSION = pkg_resources.get_distribution("pypusher").version
HOST = 'ws.pusherapp.com'
WS_PORT = 80
WSS_PORT = 443

logging.getLogger().addHandler(logging.StreamHandler())
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)



def to_json(data):
    return json.dump(data)

class PusherSocket(object):

    CLIENT_ID = 'pusher-python-client'
    PROTOCOL = 6

    __path = None
    __connected = None
    __channels = None
    __global_channels = None
    __socket_id = None

    @property
    def path(self):
        return self.__path

    @property
    def connected(self):
        return self.__connected

    @property
    def channels(self):
        return self.__channels

    @property
    def global_channels(self):
        return self.__global_channels

    @property
    def socket_id(self):
        return self.__socket_id


    def __init__(self, key, options={}):
        assert key is not None
        assert len(key)>0

        self.__path = "{ws_path}/app/{app_key}?client={CLIENT_ID}&version={VERSION}&protocol={PROTOCOL}". \
            format(
                ws_path=options.get('ws_path',''),
                app_key=key,
                CLIENT_ID=self.CLIENT_ID,
                VERSION=VERSION,
                PROTOCOL=self.PROTOCOL
            )
        self.key = key
        self.secret = options.get('secret','')
        self.__channels = Channels()
        self.__global_channel = Channel('pusher_global_channel')
        self.__global_channel.is_global = True
        self.__connected = False
        self.encrypted = options.get('encrypted') or False

        self.logger = options.get('logger') or logging.getLogger(__name__)
        self.logger.addHandler(ch)

        self.private_auth_method = options.get('private_auth_method')
        self.cert_file = options.get('cert_file')
        self.ws_host = options.get('ws_host', HOST)
        self.ws_port = options.get('ws_port', WS_PORT)
        self.wss_port = options.get('wss_port', WSS_PORT)
        self.ssl_verify = options.get('ssl_verify', True)
        self.connection = None
        self.connection_thread = None

        if self.encrypted:
            self.url = "wss://{0}:{1}{2}".format(self.ws_host, self.wss_port,self.__path)
        else:
            self.url = "ws://{0}:{1}{2}".format(self.ws_host, self.ws_port, self.__path)

        def connection_established(data):
            socket = self.__parser(data)
            self.__connected = True
            self.__socket_id = socket.get('socket_id')
            self.subscribe_all()

        self.bind('pusher:connection_established', connection_established)

        def connection_disconnected(data):
            self.__connected = False
            [c.disconnect for c in self.__channels.channels()]

        self.bind('pusher:connection_disconnected', connection_disconnected)

        def error(data):
            self.logger.fatal("Pusher : error : {0}".format(data.get('inspect')))

        self.bind('pusher:error', error)

        def ping(data):
            self.send_event('pusher:pong', None)

        self.bind('pusher:ping', ping)

    def get_channel(self, channel_name):
        return self.__channels.find(channel_name)

    def bind(self, event_name, callback):
        self.__global_channel.bind(event_name, callback)

    def connect(self, async=False):
        if self.connection:
            return
        self.logger.debug("Pusher : connecting : {0}".format(self.url))

        if async:
            def create_thread():
                try:
                    self.connect_internal()
                except Exception as e:
                    self.send_local_event("pusher:error",  e)
            self.connection_thread = Thread(None, target=create_thread)
            self.connection_thread.start()
        else:
            self.connect_internal()

    def disconnect(self):
        if not self.connection:
            return
        self.logger.debug("Pusher : disconnecting")
        self.__connected = False
        self.connection.close
        self.connection = None
        if self.connection_thread:
            self.connection_thread.join()
            self.connection_thread = None

    def subscribe(self, channel_name, user_data = None):
        if isinstance(user_data, dict):
            user_data = to_json(user_data)
        elif user_data:
            user_data = to_json({'user_id': user_data})
        elif self.is_presence_channel(channel_name):
            raise AssertionError("user_data is required for presence channels")

        channel = self.__channels.add(channel_name, user_data)
        if self.connected:
            self.authorize(channel, self.authorize_callback)
        return channel

    def unsubscribe(self, channel_name):
        channel = self.__channels.remove(channel_name)
        if channel and self.__connected:
            self.send_event('pusher:unsubscribe', {
                'channel': channel_name
            })
        return channel

    def authorize_callback(self, channel, auth_data, channel_data):
        self.send_event('pusher:subscribe', {
            'channel': channel.name,
            'auth': auth_data,
            'channel_data': channel_data
        })
        channel.acknowledge_subscription(None)

    def send_event(self, event_name, data):
        payload = to_json({
            'event': event_name,
            'data': data
        })
        self.connection.send(payload)
        self.logger.debug("Pusher : sending event : {0}".format(payload))

    def subscribe_all(self):
        [self.subscribe(v.name, v.user_data) for k, v in copy.deepcopy(self.__channels.channels)]

    def authorize(self, channel, callback):
        if self.is_private_channel(channel.name):
            auth_data = self.get_private_auth(channel)
        elif self.is_presence_channel(channel.name):
            auth_data = self.get_presence_auth(channel)
        # could both be nil if didn't require auth
        self.callback.call(channel, auth_data, channel.user_data)

    def is_private_channel(self, channel_name):
        channel_name.startswith('private-')

    def is_presence_channel(self, channel_name):
      channel_name.startswith('presence-')

    def get_private_auth(self, channel):
        if self.private_auth_method is None:
            string_to_sign = self.__socket_id + ':' + channel.name
            signature = self.hmac(self.secret, string_to_sign)
            return "{0}:{1}".format(self.key, signature)
        else:
            return self.private_auth_method.call(self.__socket_id, channel)

    def send_event(self, event_name, data):
        payload = to_json({'event': event_name, 'data': data})
        self.connection.send(payload)
        self.logger.debug("Pusher : sending event : {0}".format(payload))

    def send_channel_event(self, channel, event_name, data):
        payload = to_json({'channel': channel, 'event': event_name, 'data': data})
        self.connection.send(payload)
        self.logger.debug("Pusher : sending channel event : {0}".format(payload))

    def connect_internal(self):
        self.connection = PusherWebSocket(self.url)

        self.logger.debug("Websocket connected")

        while True:
            msg = self.connection.receive()
            print("< {}".format(msg))
            if msg is not None:
                continue
            params = self.parser(msg)
            if params['socket_id'] and params['socket_id'] == self.socket_id:
                continue

            self.send_local_event(params['event'], params['data'], params['channel'])

    def send_local_event(self, event_name, event_data, channel_name=None):
        if channel_name:
            channel = self.__channels[channel_name]
            if channel:
                channel.dispatch_with_all(event_name, event_data)


        self.__global_channel.dispatch_with_all(event_name, event_data)
        self.logger.debug("Pusher : event received : channel: {0}; event: {1}".format(channel_name, event_name))

    def parser(self, data):
        if isinstance(data, dict):
            return data
        try:
            return json.loads(data)
        except Exception as err:
            self.logger.warn(err)
            self.logger.warn("Pusher : data attribute not valid JSON - you may wish to implement your own Pusher::Client.parser")
            return data

    def hmac(self, secret, string_to_sign):
        bytestring = bytearray(secret)
        return hmac.new(bytestring, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256)

    def __getitem__(self, *args):
        channel = self.__channels.find(args[0])
        return channel