from config import WS_PORT, WIDTH, HEIGHT
from struct import Struct
from threading import Thread
from wsgiref.simple_server import make_server
from ws4py.websocket import WebSocket
from ws4py.server.wsgiutils import WebSocketWSGIApplication
from ws4py.server.wsgirefserver import (
    WSGIServer,
    WebSocketWSGIHandler,
    WebSocketWSGIRequestHandler,
)

JSMPEG_MAGIC = b'jsmp'
JSMPEG_HEADER = Struct('>4sHH')

class StreamingWebSocket(WebSocket):
    def opened(self):
        self.send(JSMPEG_HEADER.pack(JSMPEG_MAGIC, WIDTH, HEIGHT), binary=True)

class WebsocketServer:
    server = None
    thread = None

    def __init__(self, stream_width, stream_height):
        self.stream_width = stream_width
        self.stream_height = stream_height

        WebSocketWSGIHandler.http_version = '1.1'

    def run(self):
        print('Initializing websockets server on port {}'.format(WS_PORT))
        self.server = make_server(
            '', WS_PORT,
            server_class=WSGIServer,
            handler_class=WebSocketWSGIRequestHandler,
            app=WebSocketWSGIApplication(handler_cls=StreamingWebSocket))
        self.server.initialize_websockets_manager()
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.start()

    def stop(self):
        print('Shutting down websockets server')
        self.server.shutdown()
        self.thread.join()
