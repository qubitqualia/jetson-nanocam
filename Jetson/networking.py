import pickle, _pickle
import json
import socket
import sys
import uuid
from threading import Thread
from Jetson.nanocam import *
import cv2



class MediaServer:
    def __init__(self, port):
        self.port = port
        self.media_port = 5000
        self.media_path = '/home/justin/media/'
        self.sock = socket.socket()
        self.sock.bind(('0.0.0.0', self.port))
        self.sock.listen(1)
        self.CLIENT_CONNECTED = False
        self.THREAD_ACTIVE = False
        self.thread = None
        self.conn = None
        self.addr = None
        self.csicam = CSIcamera()
        self.csicam.set_flip_method(2)

    def start(self):

        while True:

            # Establish socket connection with client [BLOCKING]
            if not self.CLIENT_CONNECTED:
                print("Waiting for remote client connection...")
                self.conn, self.addr = self.sock.accept()
                print("Client connected!")
                self.CLIENT_CONNECTED = True

            # Receive requests from client [BLOCKING]
            msg = self.conn.recv(1024).decode()

            # Valid requests:
            # {type: "image", width: wwww, height: hhhh, frames: xx, interval: yy, format: "opencv"/"file"}
            # {type: "video", width: wwww, height: hhhh, duration: xx, format: "opencv"/"file"/"udp"}
            # {type: "kill"}
            _flag_VALIDMSG = False
            _json = {}

            try:
                _json = json.loads(msg)
                _flag_VALIDMSG = True
            except TypeError:
                if msg == '':
                    self.CLIENT_CONNECTED = False
                    print("Client connection closed!")
                    self.start()
                else:
                    print("Error: Invalid JSON received from client")
                    _flag_VALIDMSG = False

            if _flag_VALIDMSG:

                # Check thread status before processing request
                # If thread is active but kill request not received, then tell client that server is busy
                if self.THREAD_ACTIVE and _json["type"] != "kill":
                    if self.thread.isAlive():
                        self.conn.send(b"BUSY")
                    else:
                        self.THREAD_ACTIVE = False

                # If thread is active and kill request is received, stop pipeline to kill thread
                elif self.THREAD_ACTIVE and _json["type"] == "kill":
                    if self.thread.isAlive():
                        StreamBus.KILL_THREAD = True
                        # Need to tell client "OK" to proceed with request
                        self.conn.send(b"OK")
                    else:
                        self.THREAD_ACTIVE = False

                if not self.THREAD_ACTIVE:

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
                        _duration = _json["duration"]
                        ret_array = self.get_video(_width, _height, _duration, _format)

                        if _format == "opencv":
                            self.send_array(ret_array)

                        elif _format == "file":
                            self.send_files(ret_array)

    def get_images(self, w, h, frames, interval, format_):

        if format_ == "opencv":
            imager = ImageStream(frames, interval, sink="opencv")
            imager.connect_camera(self.csicam)
            imager.set_frames(frames)
            imager.set_interval(interval)
            img_arr, done = imager.start_stream()
            return img_arr
        elif format_ == "file":
            fname = str(uuid.uuid4()) + '.jpg'
            imager = ImageStream(frames, interval, sink="file", outfile=self.media_path + fname)
            imager.set_frames(frames)
            imager.set_interval(interval)
            f_arr, done = imager.start_stream()
            return f_arr

    def get_video(self, w, h, dur, format_):

        if format_ == "opencv":
            vid = VideoStream(dur, src="camera", sink="opencv")
            vid.connect_camera(self.csicam)
            vid.set_output_resolution(w, h)
            vid.set_timeout(dur)
            img_arr, done = vid.start_stream()
            return img_arr

        elif format_ == "file":
            fname = str(uuid.uuid4()) + '.mp4'
            vid = VideoStream(dur, src="camera", sink="file", outfile=self.media_path + fname)
            vid.connect_camera(self.csicam)
            vid.set_output_resolution(w, h)
            vid.set_timeout(dur)
            vid.start_stream()
            f_arr = [fname]
            return f_arr

        elif format_ == "udp":
            vid = VideoStream(dur, src="camera", sink="udp")
            vid.connect_camera(self.csicam)
            vid.set_output_resolution(w, h)
            vid.set_timeout(dur)
            vid.configure_udp_conn(self.addr[0], self.media_port)
            self.thread = Thread(target=vid.start_stream)
            self.THREAD_ACTIVE = True
            self.thread.start()
            return []

    def send_files(self, arr):
        print("Sending {} files to client...".format(len(arr)))
        tot_bytes = 0

        for i, fname in enumerate(arr):
            sendfile = open(self.media_path + fname, "rb")
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
        tot_bytes = 0

        data = pickle.dumps(arr, protocol=2)
        self.conn.sendall(data)
        self.conn.send(b"DONE")


class MediaClient:
    def __init__(self, host, port):
        self.hostip = host
        self.port = port
        self.media_port = 5000
        self.media_path = 'C:\\Users\\jmatt\\RemoteMedia\\'
        self.sock = socket.socket()
        self.thread = None
        self.WAIT_FOR_OK = False

    def connect(self):
        self.sock.connect((self.hostip, self.port))

    def image_request(self, frames, interval, outfile, width=3280, height=2464, display=False, override=False):
        fname = []
        img_array = []

        # Request "file" pipeline to be opened on server
        message = {"type": "image", "width": width, "height": height, "frames": frames, "interval": interval, "format": "file"}
        _json_str = json.dumps(message)
        self.sock.send(_json_str.encode())
        fname = self.fetch_images()

        if self.WAIT_FOR_OK and not override:
            print("Server is busy, try again later or override")
            self.WAIT_FOR_OK = False
            return fname
        elif self.WAIT_FOR_OK and override:
            status = self.send_kill()
            if status:
                self.fetch_images()

        if display:
            for name in fname:
                cv2.namedWindow(name, cv2.WINDOW_AUTOSIZE)
                img = cv2.imread(name)
                img_array.append(img)
                cv2.imshow(name, img)

            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return fname, img_array

    def video_request(self, duration, outfile, width=3280, height=2464, display=False, override=False, src="file"):
        fname = []
        img_array = []

        # Stream from file on server to file on client
        if src == "file":
            # Request "file" pipeline to be opened on server
            message = {"type": "video", "width": width, "height": height, "duration": duration, "format": "file"}
            _json_str = json.dumps(message)
            self.sock.send(_json_str.encode())
            fname = self.fetch_video()

            if self.WAIT_FOR_OK and not override:
                print("Server is busy, try again later or override")
                self.WAIT_FOR_OK = False
                return fname
            elif self.WAIT_FOR_OK and override:
                status = self.send_kill()
                if status:
                    self.fetch_video()

            if display:
                cap = cv2.VideoCapture(fname)
                cv2.namedWindow('Video from MediaServer', cv2.WINDOW_AUTOSIZE)

                while True:
                    ret, frame = cap.read()
                    img_array.append(frame)
                    cv2.imshow('Vidoe from MediaServer', frame)

                    if cv2.waitKey(1) == 27:
                        break  # esc to exit

                cv2.destroyAllWindows()

            return fname, img_array

        # Stream via UDP to file on client using VideoStream class
        elif src == "udp":
            f = str(uuid.uuid4()) + '.mp4'
            vid = VideoStream(duration, src="udp", sink="file", outfile=self.media_path + f)
            vid.set_timeout(duration)
            vid.set_output_resolution(width, height)
            vid.configure_udp_conn(port=self.media_port)

            # Request "udp" pipeline to be opened on server
            message = {"type": "video", "width": width, "height": height, "duration": duration, "format": "udp"}
            _json_str = json.dumps(message)
            self.sock.send(_json_str.encode())
            self.thread = Thread(target=vid.start_stream)
            self.thread.start()
            print("UDP pipeline opened. Streaming to file for {} seconds.".format(duration))

        else:
            print("Invalid source argument provided.  Valid options are \'file\' or \'udp\'.")
            return fname

    def hls_request(self, duration, hls_root, hls_playloc, hls_loc, width=3280, height=2464, override=False,
                    hls_len=10, hls_maxfiles=10, hls_duration=5):

        # Request UDP pipeline from server
        message = {"type": "video", "width": width, "height": height, "duration": duration, "format": "udp"}
        _json_str = json.dumps(message)
        self.sock.send(_json_str.encode())

        # Instantiate VideoStream object
        vid = VideoStream(duration, src="udp", sink="hls")
        vid.set_timeout(duration)
        vid.set_output_resolution(width, height)
        vid.configure_udp_conn(port=self.media_port)
        vid.configure_hls(hls_len, hls_maxfiles, hls_duration, hls_root, hls_playloc, hls_loc)

        # Wait for response from server
        data = self.sock.recv(1024)
        if data == b"OK":
            self.thread = Thread(target=vid.start_stream)
            return True
        elif data == b"WAIT":
            if override:
                status = self.send_kill()
                if status:
                    self.thread = Thread(target=vid.start_stream)
                    return True
                else:
                    return False
            else:
                print("Server is busy, try again later or override")
                return False

    def send_kill(self):
        print("Server is busy. Sending override command...")
        message = {"type": "kill"}
        _json_str = json.dumps(message)
        self.sock.send(_json_str.encode())
        print("Waiting for OK...", )
        data = self.sock.recv(1024)
        if data == b"OK":
            print("received!")
            self.WAIT_FOR_OK = False
            return True
        else:
            print("unknown response received.")
            return False

    def fetch_images(self):
        loop_count = 0
        fname_complete = False
        fname = b""
        fdata = b""
        fname_list = []
        tot_bytes = 0

        # Server response format: pickle([filename1, filename2 ... ])DONE<file1 bytes>MORE<file2 bytes>MORE...<filen bytes>QUIT
        while True:
            data = self.sock.recv(1024)

            # Check for BUSY or DONE response
            if loop_count == 0:
                if data.find(b"BUSY") != -1:
                    self.WAIT_FOR_OK = True
                    return fname_list
                else:
                    loop_count += 1
            if data.find(b"DONE") != -1:
                data_arr = data.split(b"DONE")
                fname += data_arr[0]
                fdata = data_arr[1]
                tot_bytes += sys.getsizeof(fdata)
                fname_complete = True
                try:
                    fname_list = pickle.loads(fname)
                except _pickle.UnpicklingError:
                    print("Invalid pickle packet")
                    return fname_list
                f = open(self.media_path + fname_list[0], 'wb')
                i = 0
                f.write(fdata)
            else:
                if fname_complete:
                    if data.find(b"MORE") != -1:
                        i += 1
                        data_arr = data.split(b"MORE")
                        tot_bytes += sys.getsizeof(data_arr)
                        f.write(data_arr[0])
                        f.close()
                        f = open(self.media_path + fname_list[i], 'wb')
                        f.write(data_arr[1])
                    elif data.find(b"QUIT") != -1:
                        data = data[:-4]
                        f.write(data)
                        tot_bytes += sys.getsizeof(data)
                        f.close()
                        print("Received {} kB from server".format(tot_bytes/1000))
                        return fname_list
                    else:
                        f.write(data)
                        tot_bytes += sys.getsizeof(data)
                else:
                    fname += data

    def fetch_video(self):

        loop_count = 0
        fname_complete = False
        fname = b""
        fdata = b""
        fname_list = []
        tot_bytes = 0

        # Server response format: pickle([filename])DONE<file bytes>QUIT
        while True:
            data = self.sock.recv(1024)

            # Check for BUSY or DONE response
            if loop_count == 0:
                if data.find(b"BUSY") != -1:
                    self.WAIT_FOR_OK = True
                    return fname_list
                else:
                    loop_count += 1
            if data.find(b"DONE") != -1:
                data_arr = data.split(b"DONE")
                fname += data_arr[0]
                fdata = data_arr[1]
                tot_bytes += sys.getsizeof(fdata)
                fname_complete = True
                try:
                    fname_list = pickle.loads(fname)
                except _pickle.UnpicklingError:
                    print("Invalid pickle packet")
                    return fname_list
                f = open(self.media_path + fname_list[0], 'wb')
                f.write(fdata)
            else:
                if fname_complete:
                    if data.find(b"QUIT") != -1:
                        data = data[:-4]
                        f.write(data)
                        tot_bytes += sys.getsizeof(data)
                        f.close()
                        print("Received {} kB from server".format(tot_bytes/1000))
                        return [self.media_path + fname_list[0]]
                    else:
                        f.write(data)
                        tot_bytes += sys.getsizeof(data)
                else:
                    fname += data
