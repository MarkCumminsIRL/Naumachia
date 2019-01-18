#!/usr/bin/env python3
import logging
import signal
import threading
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

import naum

class RPCRequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

is_shutdown = False
def shutdown():
    global is_shutdown
    is_shutdown = True

    logging.info('shutting down...')
    server.shutdown()

def sig_handler(num, frame):
    if not is_shutdown:
        threading.Thread(target=shutdown).start()

def main():
    logging.basicConfig(level=logging.DEBUG, format='[{asctime:s}] {levelname:s}: {message:s}', style='{')

    manager = naum.Manager()

    global server
    server = SimpleXMLRPCServer(('0.0.0.0', 8000), requestHandler=RPCRequestHandler, logRequests=False, allow_none=True)

    # shutdown handler
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    server.register_instance(manager)

    # rpc loop
    server.serve_forever()
    server.server_close()

    logging.info('cleaning up...')

    manager._stop()

if __name__ == "__main__":
    main()
