from http.server import BaseHTTPRequestHandler
from datetime import datetime
from time import time
import json
import os

class HttpHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.path == '/screenshots':
            content_type = 'application/json; charset=utf-8'
            _, _, content = next(os.walk('./screenshots'))
            content = ['/screenshots/' + x for x in content]
            content = json.dumps(content).encode('utf-8')
        elif self.path.startswith('/screenshots/'):
            filename = self.path[1:]  # Remove first slash
            with open(filename, 'rb') as f:
                content = f.read()
                content_type = 'image/jpeg'
        else:
            print(self.path)
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(content))
        self.send_header('Last-Modified', self.date_time_string(time()))
        self.end_headers()
        if self.command == 'GET':
            self.wfile.write(content)

    def do_POST(self):
        print(self.path)
        if self.path == '/screenshot':
            now = datetime.now()
            filename = now.strftime('%d-%m-%Y_%H-%M-%S') + '.jpg'
            response = ('/screenshots/' + filename).encode('utf-8')
            self.server.camera.capture('screenshots/' + filename)
            self.send_response(201)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(response))
            self.send_header('Last-Modified', self.date_time_string(time()))
            self.end_headers()
            self.wfile.write(response)
        elif self.path == '/record':
            print('Starting recording')
            now = datetime.now()
            filename = now.strftime('%d-%m-%Y_%H-%M-%S') + '.h264'
            full_path = 'videos/' + filename
            self.server.camera.start_recording(full_path, splitter_port=2)
            self.server.camera.wait_recording(2)
            self.server.camera.stop_recording(splitter_port=2)


            # self.server.camera_output.start_recording()
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()