import logging

from pypusher.channel import Channel

class Channels(object):


    __channels = {}

    @property
    def channels(self):
        return self.__channels

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.__channels = {}

    def add(self, channel_name, user_data):
        if self.__channels.get(channel_name) is None:
            self.__channels[channel_name] = Channel(channel_name, user_data, self.logger)
        return self.__channels[channel_name]

    def find(self, channel_name):
        return self.__channels.get(channel_name)

    def remove(self, channel_name):
        del self.__channels[channel_name]

    def empty(self):
        return len(self.__channels.keys())==0

    def size(self):
        return len(self.__channels.keys())