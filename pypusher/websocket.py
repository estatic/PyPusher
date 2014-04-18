
from websocket import create_connection
import logging

class PusherWebSocket(object):

    client = None

    def __init__(self, url, params={}):
        #if not self.client:
        self.client = create_connection(url)
        self.logger = params.get('logger') or logging.getLogger()


    def send(self, data, type='text'):
        yield from self.client(data)


    def receive(self):
        answer = self.client.recv()
        return answer

    def close(self):
        self.client.close()