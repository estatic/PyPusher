from pypusher.socket import PusherSocket
import logging

root = logging.getLogger()
root.setLevel(logging.DEBUG)

sock = PusherSocket('cb65d0a7a72cd94adf1f', { 'encrypted': True, 'logger':root })

subs = sock.subscribe('ticker.3')

def handle_res(*args, **kw):
    root.info(">>>> ARGS: %s" % args)
    root.info(">>>> KW: %s" % kw)

sock['ticker.3'].bind('message', handle_res)

sock.connect()