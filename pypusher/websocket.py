
from websocket import create_connection
import logging

class PusherWebSocket(object):

    client = None

    def __init__(self, url, params=None):
        if params is None:
            params={}
        self.client = create_connection(url)
        self.logger = params.get('logger') or logging.getLogger(__name__)


    def send(self, data):
        self.logger.debug("< SEND: %s" % data)
        self.client.send(data)


    def receive(self):
        answer = self.client.recv()
        self.logger.debug("> RECEIVE: %s" % answer)
        return answer

    def close(self):
        self.client.close()