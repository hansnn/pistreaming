from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta
from time import time
from http.server import HTTPServer
from threading import Thread
from config import HTTP_PORT, RECORD_SECONDS_AT_A_TIME
import json
import os

class Recorder:
    def __init__(self, camera):
        self.camera = camera
        self.stop_recording_at = None
        self.thread = None

    def start_or_bump_recording(self):
        now = datetime.now()
        should_start_recording = self.stop_recording_at is None
        self.stop_recording_at = now + timedelta(0, RECORD_SECONDS_AT_A_TIME)
        if should_start_recording:
            print('Starting recording thread')
            self.thread = Thread(target=self.record, args=(now,))
            self.thread.start()
        else:
            print('Bumping recording')

    def record(self, started_at):
        filename = started_at.strftime('%d-%m-%Y_%H-%M-%S') + '.h264'
        full_path = 'videos/' + filename
        self.camera.start_recording(full_path, splitter_port=2)
        print('Starting recording for {}'.format(full_path))
        while self.stop_recording_at is not None and self.stop_recording_at > datetime.now():
            print('Still recording')
            self.camera.wait_recording(2)
        self.camera.stop_recording(splitter_port=2)
        self.thread = None
        self.stop_recording_at = None
        print('Stopped recording')

    def stop_recording(self):
        self.stop_recording_at = None

    def kill_recording(self):
        self.stop_recording()
        if self.thread is not None:
            self.thread.join()


class StreamingHttpServer(HTTPServer):
    def __init__(self, camera, recorder):
        super(StreamingHttpServer, self).__init__(('', HTTP_PORT), HttpHandler)
        self.camera = camera
        self.recorder = recorder


class HttpHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.json_response()

    def do_GET(self):
        if self.path == '/screenshots':
            _, _, content = next(os.walk('./screenshots'))
            self.json_response(200, ['/screenshots/' + x for x in content])
            return
        elif self.path.startswith('/screenshots/'):
            filename = self.path[1:]  # Remove first slash from '/screenshots/<file>'
            with open(filename, 'rb') as f:
                self.image_response(f.read())
            return
        else:
            self.send_error(404)
            return

    def do_POST(self):
        if self.path == '/screenshot':
            now = datetime.now()
            filename = now.strftime('%d-%m-%Y_%H-%M-%S') + '.jpg'
            full_path = 'screenshots/{}'.format(filename)
            self.server.camera.capture(full_path)
            self.json_response(201, {'screenshot': '/{}'.format(full_path)})
        elif self.path == '/record':
            self.server.recorder.start_or_bump_recording()
            self.json_response()

    def json_response(self, status=204, response=None):
        self.send_response(status)
        self.send_common_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        if response is not None:
            response = json.dumps(response).encode('utf-8')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.end_headers()

    def image_response(self, img):
        self.send_response(200)
        self.send_common_headers()
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', str(len(img)))
        self.end_headers()
        self.wfile.write(img)

    def send_common_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Last-Modified', self.date_time_string(int(time())))


class HttpServer:
    server = None
    thread = None

    def __init__(self, camera):
        self.camera = camera
        self.recorder = Recorder(camera)

    def run(self):
        print('Initializing http server on port {}'.format(HTTP_PORT))

        self.server = StreamingHttpServer(self.camera, self.recorder)
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.start()

    def stop(self):
        print('Shutting down http server')
        self.server.shutdown()
        self.thread.join()
        self.recorder.kill_recording()
