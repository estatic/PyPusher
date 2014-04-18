from pypusher.socket import PusherSocket

sock = PusherSocket('cb65d0a7a72cd94adf1f', { 'encrypted': True })
subs = sock.subscribe('ticker.160')
sock['ticker.160'].bind('hello', lambda x: print(x))
sock.connect()