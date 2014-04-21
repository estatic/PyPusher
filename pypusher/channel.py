import logging

class Channel(object):

    def __init__(self, channel_name, user_data=None, logger=None):
        self.name = channel_name
        self.user_data = user_data
        self.logger = logger or logging.getLogger(__name__)
        self.is_global = False
        self.callbacks = {}
        self.subscribed = False

    def bind(self, event_name, callback):
        self.logger.debug("Binding {0} to {1}".format(event_name, self.name))
        self.callbacks[event_name] = self.callbacks.get(event_name) or []
        self.callbacks[event_name].append((callback))

    def dispatch_with_all(self, event_name, data):
      self.dispatch(event_name, data)

    def dispatch(self, event_name, data):
        is_global = 'global '
        if not self.is_global:
            is_global = ''
        self.logger.debug("Dispatching {0}callbacks for {1}".format(is_global,event_name))

        self.logger.debug("CHANNELS LIST: [{0}]".format(', '.join(self.callbacks.keys())))

        if self.callbacks.get(event_name):
            for callback in self.callbacks[event_name]:
                callback(data)
        else:
            self.logger.debug("No {0}callbacks to dispatch for {1}".format(is_global, event_name))

    def acknowledge_subscription(self, data):
      self.subscribed = True


class NullChannel(object):
    def __init__(self, channel_name, *args):
        self.name = channel_name

    def method_missing(self, *a):
        raise NotImplemented("Channel `{0}` hasn't been subscribed yet.".format(self.name))
