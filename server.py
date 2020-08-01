#!/usr/bin/env python

import io
import os
import picamera
from config import WIDTH, HEIGHT, FRAMERATE, VFLIP, HFLIP
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep
from HttpServer import HttpServer
from WebsocketServer import WebsocketServer


class CameraOutput(object):
    def __init__(self, camera):
        print('Spawning background conversion process')
        self.converter = Popen([
            'ffmpeg',
            '-f', 'rawvideo',
            '-pix_fmt', 'yuv420p',
            '-s', '%dx%d' % camera.resolution,
            '-r', str(float(camera.framerate)),
            '-i', '-',
            '-f', 'mpeg1video',
            '-b', '800k',
            '-r', str(float(camera.framerate)),
            '-'],
            stdin=PIPE, stdout=PIPE, stderr=io.open(os.devnull, 'wb'),
            shell=False, close_fds=True)
        self.recording = False

    def write(self, b):
        self.converter.stdin.write(b)

    def flush(self):
        print('Waiting for background conversion process to exit')
        self.converter.stdin.close()
        self.converter.wait()

    def close(self):
        self.converter.stdout.close()


class BroadcastThread(Thread):
    def __init__(self, converter, websocket_server):
        super(BroadcastThread, self).__init__()
        self.converter = converter
        self.websocket_server = websocket_server

    def run(self):
        try:
            while True:
                buf = self.converter.stdout.read1(32768)
                if buf:
                    self.websocket_server.server.manager.broadcast(buf, binary=True)
                elif self.converter.poll() is not None:
                    break
        finally:
            self.converter.stdout.close()


def main():
    print('Initializing camera')
    with picamera.PiCamera() as camera:
        camera.resolution = (WIDTH, HEIGHT)
        camera.framerate = FRAMERATE
        camera.vflip = VFLIP  # flips image rightside up, as needed
        camera.hflip = HFLIP  # flips image left-right, as needed
        camera.drc_strength = 'high'
        sleep(1)  # camera warm-up time

        websocket_server = WebsocketServer(WIDTH, HEIGHT)
        output = CameraOutput(camera)
        broadcast_thread = BroadcastThread(output.converter, websocket_server)
        http_server = HttpServer(camera)
        print('Starting recording')
        camera.start_recording(output, 'yuv')
        try:
            websocket_server.run()
            http_server.run()
            print('Initializing broadcast thread')
            broadcast_thread.start()
            print('Everything initialized. Streaming...')
            while True:
                camera.wait_recording(1)
        except KeyboardInterrupt:
            pass
        finally:
            print('Stopping recording')
            camera.stop_recording()
            print('Waiting for broadcast thread to finish')
            broadcast_thread.join()
            http_server.stop()
            websocket_server.stop()


if __name__ == '__main__':
    main()
