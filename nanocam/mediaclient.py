import socket
from threading import Thread
import time
import json
import cv2
import sys
import pickle, _pickle

if sys.platform == 'linux':
    from nanocam.tools import VideoStream


class MediaClient:
    def __init__(self):
        self.hostip = ''         # IP address of server
        self.port = 0            # Messaging port
        self.media_port = 5004   # Media port
        self.media_path = ''     # Directory for saving images/videos
        self.sock = socket.socket()
        self.thread = None
        self.thread2 = None
        self.WAIT_FOR_OK = False
        self.vid = None

    def set_hostip(self, host):
        self.hostip = host

    def set_msg_port(self, port):
        self.port = port

    def set_media_path(self, path):
        self.media_path = path

    def connect(self):
        # Check if socket is already connected
        try:
            self.sock.send(b"OK")
        except OSError:
            self.sock = socket.socket()
            self.sock.connect((self.hostip, self.port))

    def flush(self):
        self.sock.send(b"GOODBYE")
        self.sock.close()

    def listen_for_close(self):
        # Deprecated

        print("Waiting for kill request from server to close UDP pipeline...")
        data = self.sock.recv(1024).decode()
        _json = json.loads(data)
        if _json["type"] == "kill":
            print("Kill request received! Closing pipeline...")
            self.vid.Gstobj.quit()

    def start_threads(self):
        time.sleep(0.1)
        self.thread = Thread(target=self.vid.start_stream, args=())
        self.thread.start()

    def get_stream_status(self):
        status = False
        try:
            if self.thread.is_alive():
                status = True
            else:
                status = False
        except AttributeError:
            status = True

        return status

    def image_request(self, frames, interval, width=3280, height=2464, display=False, override=False):
        # Fetch a series of images from the server camera
        # frames - number of frames to capture
        # interval - time interval between frames
        # width - output width of retrieved frames
        # height - output height of retrieved frames
        # display - display images immediately upon receipt
        # override - issue command to server to immediately close any existing pipelines to process this one
        # Returns tuple of arrays - filenames, images

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
        # Fetch a video from the server camera
        # duration - length of time to stream in seconds
        # width - output width of retrieved video
        # height - output height of retrieved video
        # display - display video immediately upon receipt
        # override - issue command to server to immediately close any existing pipelines to process this one
        # src - select source for video stream on the client side (e.g. "file", "udp")
        # Returns tuple of arrays - filenames, images

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
            if sys.platform == 'linux':
                self.vid = VideoStream(duration, src="udp", sink="file")
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
        # Activate an HLS stream on the server
        # duration - length of time to stream in seconds
        # hls_root - root location for HLS (e.g. http://localhost/)
        # hls_playloc - location of m3u8 file (e.g. /var/www/public/stream0.m3u8)
        # hls_loc - location of fragment files (e.g. /var/www/public/fragment%05d.ts)
        # width - output width of HLS stream
        # height - output height of HLS stream
        # override - issue command to server to close any existing pipelines to process this one
        # hls_len - length of HLS playlist
        # hls_maxfiles - maximum number of HLS files
        # hls_duration - target duration for HLS fragments in seconds

        # Request UDP pipeline from server
        message = {"type": "video", "width": width, "height": height, "duration": duration, "format": "udp"}
        _json_str = json.dumps(message)
        self.sock.send(_json_str.encode())

        # Instantiate VideoStream object
        if sys.platform == 'linux':
            self.vid = VideoStream(duration, src="udp", sink="hls")
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

    def send_timer_reset(self, duration):
        message = {"type": "reset_timer", "duration": str(duration)}
        _json_str = json.dumps(message)
        self.sock.send(_json_str.encode())

    def send_kill(self):
        # This function is called automatically whenever override flag is set to True
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



