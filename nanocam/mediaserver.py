import pickle, _pickle
import json
import socket
from threading import Thread
from nanocam import tools, globals
import sys

class MediaServer:
    def __init__(self, port):
        self.port = port            # Port for messaging
        self.media_port = 5004      # Port for streaming media via UDP
        self.media_path = ''        # Working directory for server images/videos
        self.sock = socket.socket()
        self.sock.bind(('0.0.0.0', self.port))
        self.sock.listen(1)
        self.CLIENT_CONNECTED = False
        self.THREAD_ACTIVE = False
        self.WAIT_FOR_CLOSE = False
        self.last_json = {}
        self.thread = None
        self.conn = None
        self.addr = None
        self.vid = None
        self.timer = None
        self.csicam = tools.CSIcamera()

    def start(self):

        while True:

            # Establish socket connection with client [BLOCKING]
            if not self.CLIENT_CONNECTED:
                print("Waiting for remote client connection...",)
                self.conn, self.addr = self.sock.accept()
                print("Client connected!")
                self.CLIENT_CONNECTED = True

            # Receive requests from client [BLOCKING]
            print("Listening for client requests...",)
            try:
                msg = self.conn.recv(1024).decode()
            except ConnectionResetError:
                self.CLIENT_CONNECTED = False
            print("received new message!")

            # Valid requests:
            # {type: "image", width: wwww, height: hhhh, frames: xx, interval: yy, format: "opencv"/"file"}
            # {type: "video", width: wwww, height: hhhh, duration: xx, format: "opencv"/"file"/"udp"}
            # {type: "kill"}
            # {type: "reset_timer", duration: xx}
            _flag_VALIDMSG = False
            _json = {}

            # Check for valid JSON from client
            try:
                _json = json.loads(msg)
                _flag_VALIDMSG = True
            except json.decoder.JSONDecodeError:
                if msg == '':
                    self.CLIENT_CONNECTED = False
                    print("Client connection closed!")
                elif msg == b"GOODBYE":
                    self.CLIENT_CONNECTED = False
                    print("Client object destroyed")
                else:
                    print("Error: Invalid JSON received from client")
                    _flag_VALIDMSG = False

            if _flag_VALIDMSG:

                # Check for active local streams that require shutdown prior to fulfilling client request
                if globals.StreamStatus.LOCAL_BUSY and _json["type"] != "kill":
                    print("Stream already being processed on server. Sending BUSY response to client")
                    self.last_json = _json
                    self.conn.send(b"BUSY")
                elif globals.StreamStatus.LOCAL_BUSY and _json["type"] == "kill":
                    if self.last_json["format"] == "udp":
                        print("Kill request received from client. Shutting down the pipeline!")
                        self.conn.send(b"OK")
                        _json = self.last_json
                    globals.StreamStatus.LOCAL_KILL = True
                    self.WAIT_FOR_CLOSE = True
                elif "format" in _json:
                    if not globals.StreamStatus.LOCAL_BUSY and _json["format"] == "udp":
                        self.conn.send(b"OK")

                # If kill command received from client, wait for pipeline to close before proceeding with request
                print("Waiting for pipeline to close...",)
                if self.WAIT_FOR_CLOSE:
                    self.WAIT_FOR_CLOSE = False
                    while globals.StreamStatus.LOCAL_BUSY:
                        pass
                    print("done!")

                # Process request from client
                if not globals.StreamStatus.LOCAL_BUSY:
                    _type = _json["type"]
                    _width = int(_json["width"])
                    _height = int(_json["height"])
                    _format = _json["format"]

                    if _type == "image":
                        _frames = int(_json["frames"])
                        _interval = int(_json["interval"])
                        ret_array = self.get_images(_width, _height, _frames, _interval, _format)

                        if _format == "opencv":
                            self.send_array(ret_array)

                        elif _format == "file":
                            # Send image filenames
                            self.send_array(ret_array)

                            # Send image files
                            self.send_files(ret_array)

                    elif _type == "video":
                        _duration = int(_json["duration"])
                        ret_array = self.get_video(_width, _height, _duration, _format)

                        if _format == "opencv":
                            self.send_array(ret_array)

                        elif _format == "file":
                            self.send_array(ret_array)
                            self.send_files(ret_array)
                # New
                else:

                    if _json["type"] == "reset_timer":
                        if self.vid is not None:
                            self.vid.Gstobj.update_timer(int(_json["duration"]))

    def get_images(self, w, h, frames, interval, format_):

        # Returns array of images to the client
        if format_ == "opencv":
            print("Processing image request [OpenCV sink]...")
            imager = tools.ImageStream(frames, interval, sink="opencv")
            imager.connect_camera(self.csicam)
            imager.set_frames(frames)
            imager.set_interval(interval)
            img_arr = imager.start_stream()
            return img_arr

        # Returns array of filenames to the client
        elif format_ == "file":
            print("Processing image request [File sink]...")
            imager = tools.ImageStream(frames, interval, sink="file")
            imager.connect_camera(self.csicam)
            imager.set_frames(frames)
            imager.set_interval(interval)
            f_arr = imager.start_stream()
            return f_arr

    def get_video(self, w, h, dur, format_):

        # Returns array of images to the client
        if format_ == "opencv":
            print("Processing video request [OpenCV sink]...")
            vid = tools.VideoStream(dur, src="camera", sink="opencv")
            vid.connect_camera(self.csicam)
            vid.set_output_resolution(w, h)
            img_arr = vid.start_stream()
            return img_arr

        # Returns filename of video to client in array of length 1
        elif format_ == "file":
            print("Processing video request [File sink]...")
            vid = tools.VideoStream(dur, src="camera", sink="file")
            vid.connect_camera(self.csicam)
            vid.set_output_resolution(w, h)
            f_arr = vid.start_stream()
            return f_arr

        elif format_ == "udp":
            print("Processing video request [UDP sink]...")
            self.vid = tools.VideoStream(dur, src="camera", sink="udp")
            self.vid.connect_camera(self.csicam)
            self.vid.set_output_resolution(w, h)
            self.vid.configure_udp_conn(self.addr[0], self.media_port)
            self.thread = Thread(target=self.vid.start_stream, args=())
            self.thread.start()
            print("UDP pipeline opened. Streaming to client {}:{} for {} seconds.".format(self.addr[0], self.media_port, dur))
            self.THREAD_ACTIVE = True
            return []

    def get_stream_status(self):
        status = False
        if self.thread.is_alive():
            status = True
        else:
            status = False

        return status

    def close_pipeline(self):
        print("Sending command to client to close pipeline...")
        _json = {"type": "kill"}
        _json_str = json.dumps(_json)
        self.conn.send(_json_str.encode())
        self.timer.cancel()
        self.timer = None
        self.start()

    def send_files(self, arr):
        print("Sending {} files to client...".format(len(arr)))
        tot_bytes = 0

        for i, fname in enumerate(arr):
            sendfile = open(fname, "rb")
            data = sendfile.read(1024)
            _bytes = sys.getsizeof(data)
            while data:
                self.conn.send(data)
                data = sendfile.read(1024)
                _bytes += sys.getsizeof(data)
            sendfile.close()
            tot_bytes += _bytes
            _bytes = 0
            if i != len(arr) - 1:
                self.conn.send(b"MORE")
            else:
                self.conn.send(b"QUIT")

        print("Transfer complete! {} kB sent to client".format(tot_bytes/1000))

    def send_array(self, arr):
        print("Sending array to client...")
        tot_bytes = sys.getsizeof(arr)

        data = pickle.dumps(arr, protocol=2)
        self.conn.sendall(data)
        self.conn.send(b"DONE")

        print("Transfer complete! {} kB sent to client".format(tot_bytes/1000))




