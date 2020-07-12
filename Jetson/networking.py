import pickle, _pickle
import json
import socket
import sys
import uuid
from threading import Thread, Timer
from Jetson.nanocam import *
import cv2



class MediaServer:
    def __init__(self, port):
        self.port = port
        self.media_port = 5004
        self.media_path = '/home/justin/media/'
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
        self.csicam = CSIcamera()

    def start(self):

        while True:

            # Establish socket connection with client [BLOCKING]
            if not self.CLIENT_CONNECTED:
                print("Waiting for remote client connection...")
                self.conn, self.addr = self.sock.accept()
                print("Client connected!")
                self.CLIENT_CONNECTED = True

            # Receive requests from client [BLOCKING]
            print("Listening for client requests...")
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
            except json.decoder.JSONDecodeError:
                if msg == '':
                    self.CLIENT_CONNECTED = False
                    print("Client connection closed!")
                    self.start()
                else:
                    print("Error: Invalid JSON received from client")
                    _flag_VALIDMSG = False

            if _flag_VALIDMSG:

                # Check for active local streams that require shutdown prior to fulfilling client request
                if StreamStatus.LOCAL_BUSY and _json["type"] != "kill":
                    print("Sending BUSY response to client")
                    self.last_json = _json
                    self.conn.send(b"BUSY")
                elif StreamStatus.LOCAL_BUSY and _json["type"] == "kill":
                    if self.last_json["format"] == "udp":
                        print("Kill request received from client. Shutting down pipeline!")
                        self.conn.send(b"OK")
                        _json = self.last_json
                    StreamStatus.LOCAL_KILL = True
                    self.WAIT_FOR_CLOSE = True
                elif "format" in _json:
                    if not StreamStatus.LOCAL_BUSY and _json["format"] == "udp":
                        self.conn.send(b"OK")

                # Check thread status before processing request
                # If thread is active but kill request not received, then tell client that server is busy
                # OK/BUSY response is *required* for UDP requests
                # if self.THREAD_ACTIVE and _json["type"] != "kill":
                #     if self.thread.is_alive():
                #         self.conn.send(b"BUSY")
                #     else:
                #         if _json["format"] == "udp":
                #             self.conn.send(b"OK")
                #         self.THREAD_ACTIVE = False
                # elif not self.THREAD_ACTIVE and _json["format"] == "udp":
                #     self.conn.send(b"OK")
                #
                # # If thread is active and kill request is received, stop pipeline to kill thread
                # elif self.THREAD_ACTIVE and _json["type"] == "kill":
                #     if self.thread.is_alive():
                #         StreamBus.KILL_THREAD = True
                #         # Need to tell client "OK" to proceed with request
                #         self.conn.send(b"OK")
                #     else:
                #         self.THREAD_ACTIVE = False

                #if not self.THREAD_ACTIVE and not StreamStatus.LOCAL_BUSY:
                print("Waiting for pipeline to close...",)
                if self.WAIT_FOR_CLOSE:
                    self.WAIT_FOR_CLOSE = False
                    while StreamStatus.LOCAL_BUSY:
                        pass
                    print("done!")

                if not StreamStatus.LOCAL_BUSY:
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

    def get_images(self, w, h, frames, interval, format_):

        if format_ == "opencv":
            imager = ImageStream(frames, interval, sink="opencv")
            imager.connect_camera(self.csicam)
            imager.set_frames(frames)
            imager.set_interval(interval)
            img_arr = imager.start_stream()
            return img_arr
        elif format_ == "file":
            imager = ImageStream(frames, interval, sink="file")
            imager.connect_camera(self.csicam)
            imager.set_frames(frames)
            imager.set_interval(interval)
            f_arr = imager.start_stream()
            return f_arr

    def get_video(self, w, h, dur, format_):

        if format_ == "opencv":
            vid = VideoStream(dur, src="camera", sink="opencv")
            vid.connect_camera(self.csicam)
            vid.set_output_resolution(w, h)
            #vid.set_timeout(dur)
            img_arr = vid.start_stream()
            del vid
            return img_arr

        elif format_ == "file":
            vid = VideoStream(dur, src="camera", sink="file")
            vid.connect_camera(self.csicam)
            vid.set_output_resolution(w, h)
            #vid.set_timeout(dur)
            f_arr = vid.start_stream()
            del vid
            return f_arr

        elif format_ == "udp":
            self.vid = VideoStream(dur, src="camera", sink="udp")
            self.vid.connect_camera(self.csicam)
            self.vid.set_output_resolution(w, h)
            self.vid.configure_udp_conn(self.addr[0], self.media_port)
            print("IP Address of host: {}".format(self.addr[0]))
            print("Port: {}".format(self.media_port))
            self.thread = Thread(target=self.vid.start_stream, args=())
            self.thread.start()
            print("UDP pipeline opened. Streaming to client for {} seconds.".format(dur))
            #self.timer = Timer(dur+1, self.close_pipeline)
            #self.timer.start()
            self.THREAD_ACTIVE = True
            return []

    def close_pipeline(self):
        print("Sending command to client to close pipeline...")
        _json = {"type": "kill"}
        _json_str = json.dumps(_json)
        self.conn.send(_json_str.encode())
        self.timer.cancel()
        #self.thread.join()
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
        tot_bytes = 0

        data = pickle.dumps(arr, protocol=2)
        self.conn.sendall(data)
        self.conn.send(b"DONE")


class MediaClient:
    def __init__(self, host, port):
        self.hostip = host
        self.port = port
        self.media_port = 5004
        self.media_path = 'C:\\Users\\jmatt\\RemoteMedia\\'
        self.sock = socket.socket()
        self.thread = None
        self.thread2 = None
        self.WAIT_FOR_OK = False
        self.vid = None

    def connect(self):
        self.sock.connect((self.hostip, self.port))

    def listen_for_close(self):
        print("Waiting for kill request from server to close UDP pipeline...")
        data = self.sock.recv(1024).decode()
        _json = json.loads(data)
        if _json["type"] == "kill":
            print("Kill request received! Closing pipeline...")
            self.vid.Gstobj.quit()

    def start_threads(self):
        #self.thread2 = Thread(target=self.listen_for_close, args=())
        #self.thread2.start()
        time.sleep(0.1)
        self.thread = Thread(target=self.vid.start_stream, args=())
        self.thread.start()

    def image_request(self, frames, interval, width=3280, height=2464, display=False, override=False):
        fname = []
        img_array = []

        # Request "file" pipeline to be opened on server
        message = {"type": "image", "width": width, "height": height, "frames": frames, "interval": interval, "format": "file"}
        _json_str = json.dumps(message)
        self.sock.send(_json_str.encode())
        fname = self.fetch_images()

        # fetch_images call will check for b"BUSY" and set WAIT_FOR_OK flag if received
        if self.WAIT_FOR_OK and not override:
            print("Server is busy, try again later or override")
            self.WAIT_FOR_OK = False
            return fname
        elif self.WAIT_FOR_OK and override:
            status = self.send_kill()
            if status:
                fname = self.fetch_images()

        if display:
            for name in fname:
                cv2.namedWindow(name, cv2.WINDOW_AUTOSIZE)
                img = cv2.imread(name)
                img_array.append(img)
                img = cv2.resize(img, (640, 480))
                cv2.imshow(name, img)

            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return fname, img_array

    def video_request(self, duration, width=3280, height=2464, display=False, override=False, src="file"):
        fname = []
        img_array = []

        # Stream from file on server to file on client
        if src == "file":
            # Request "file" pipeline to be opened on server
            message = {"type": "video", "width": width, "height": height, "duration": duration, "format": "file"}
            _json_str = json.dumps(message)
            self.sock.send(_json_str.encode())
            fname = self.fetch_video()

            # fetch_video call will check for b"BUSY" and set WAIT_FOR_OK flag if received
            if self.WAIT_FOR_OK and not override:
                print("Server is busy, try again later or override")
                self.WAIT_FOR_OK = False
                return fname
            elif self.WAIT_FOR_OK and override:
                status = self.send_kill()
                if status:
                    fname = self.fetch_video()

            if display:
                print("Displaying video {}".format(fname[0]))
                cap = cv2.VideoCapture(fname[0])
                cv2.namedWindow('Video from MediaServer', cv2.WINDOW_AUTOSIZE)

                while True:
                    ret, frame = cap.read()
                    img_array.append(frame)
                    frame = cv2.resize(frame, (640, 480))
                    cv2.imshow('Video from MediaServer', frame)

                    if cv2.waitKey(1) == 27:
                        break  # esc to exit

                cv2.destroyAllWindows()

            return fname, img_array

        # Stream via UDP to file on client using VideoStream class
        elif src == "udp":
            self.vid = VideoStream(duration, src="udp", sink="file")
            #self.vid.set_timeout(duration)
            self.vid.set_output_resolution(width, height)
            self.vid.configure_udp_conn(port=self.media_port)

            # Request "udp" pipeline to be opened on server
            message = {"type": "video", "width": width, "height": height, "duration": duration, "format": "udp"}
            _json_str = json.dumps(message)
            self.sock.send(_json_str.encode())

            # Wait for response from server
            data = self.sock.recv(1024)
            if data == b"OK":
                self.WAIT_FOR_OK = False
                self.start_threads()
            elif data == b"BUSY":
                self.WAIT_FOR_OK = True

            # Issue override command if enabled and server is busy
            if self.WAIT_FOR_OK and not override:
                print("Server is busy, try again later or override")
                self.WAIT_FOR_OK = False
                return fname, img_array
            elif self.WAIT_FOR_OK and override:
                status = self.send_kill()
                if status:
                    self.start_threads()

            print("UDP pipeline opened. Streaming to file for {} seconds.".format(duration))
            self.thread2.join()
            self.thread.join()
            return fname, img_array

        else:
            print("Invalid source argument provided.  Valid options are \'file\' or \'udp\'.")
            return fname, img_array

    def hls_request(self, duration, hls_root, hls_playloc, hls_loc, width=3280, height=2464, override=False,
                    hls_len=10, hls_maxfiles=10, hls_duration=5):

        # Request UDP pipeline from server
        message = {"type": "video", "width": width, "height": height, "duration": duration, "format": "udp"}
        _json_str = json.dumps(message)
        self.sock.send(_json_str.encode())

        # Instantiate VideoStream object
        self.vid = VideoStream(duration, src="udp", sink="hls")
        #self.vid.set_timeout(duration)
        self.vid.set_output_resolution(width, height)
        self.vid.configure_udp_conn(port=self.media_port)
        self.vid.configure_hls(hls_len, hls_maxfiles, hls_duration, hls_root, hls_playloc, hls_loc)

        # Wait for response from server
        print("Waiting for OK from server...",)
        data = self.sock.recv(1024)
        if data == b"OK":
            print("OK! Starting stream.")
            self.start_threads()
            return True
        elif data == b"BUSY":
            print("BUSY!")
            if override:

                status = self.send_kill()
                if status:
                    self.start_threads()
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
        print("Waiting for OK...",)
        data = self.sock.recv(1024)
        if data == b"OK":
            print("OK!")
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
        fname_list_in = []
        fname_list_out = []
        tot_bytes = 0

        # Server response format: pickle([filename1, filename2 ... ])DONE<file1 bytes>MORE<file2 bytes>MORE...<filen bytes>QUIT
        while True:
            data = self.sock.recv(1024)

            # Check for BUSY or DONE response
            if loop_count == 0:
                if data.find(b"BUSY") != -1:
                    self.WAIT_FOR_OK = True
                    return fname_list_out
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
                    for _file in fname_list:
                        file_name = _file.split('/')[-1]
                        file_name = file_name.replace(':', '+')
                        fname_list_out.append(self.media_path + file_name)
                except _pickle.UnpicklingError:
                    print("Invalid pickle packet")
                    return fname_list_out

                f = open(fname_list_out[0], 'wb')
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
                        f = open(fname_list_out[i], 'wb')
                        f.write(data_arr[1])
                    elif data.find(b"QUIT") != -1:
                        data = data[:-4]
                        f.write(data)
                        tot_bytes += sys.getsizeof(data)
                        f.close()
                        print("Received {} kB from server".format(tot_bytes/1000))
                        return fname_list_out
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
                    fname_list[0] = fname_list[0].split('/')[-1]
                    fname_list[0] = self.media_path + fname_list[0].replace(':', '+')
                except _pickle.UnpicklingError:
                    print("Invalid pickle packet")
                    return fname_list
                f = open(fname_list[0], 'wb')
                f.write(fdata)
            else:
                if fname_complete:
                    if data.find(b"QUIT") != -1:
                        data = data[:-4]
                        f.write(data)
                        tot_bytes += sys.getsizeof(data)
                        f.close()
                        print("Received {} kB from server".format(tot_bytes/1000))
                        return [fname_list[0]]
                    else:
                        f.write(data)
                        tot_bytes += sys.getsizeof(data)
                else:
                    fname += data





