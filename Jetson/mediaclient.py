import pickle, _pickle
import json
import socket
import sys
import uuid
from threading import Thread
import cv2
#from Jetson.nanocam import *

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

    def image_request(self, frames, interval, width=3280, height=2464, display=False, override=False):
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
            pass
            # f = str(uuid.uuid4()) + '.mp4'
            # vid = VideoStream(duration, src="udp", sink="file", outfile=self.media_path + f)
            # vid.set_timeout(duration)
            # vid.set_output_resolution(width, height)
            # vid.configure_udp_conn(port=self.media_port)
            #
            # # Request "udp" pipeline to be opened on server
            # message = {"type": "video", "width": width, "height": height, "duration": duration, "format": "udp"}
            # _json_str = json.dumps(message)
            # self.sock.send(_json_str.encode())
            # self.thread = Thread(target=vid.start_stream)
            # self.thread.start()
            # print("UDP pipeline opened. Streaming to file for {} seconds.".format(duration))

        else:
            print("Invalid source argument provided.  Valid options are \'file\' or \'udp\'.")
            return fname

    def hls_request(self, duration, hls_root, hls_playloc, hls_loc, width=3280, height=2464, override=False,
                    hls_len=10, hls_maxfiles=10, hls_duration=5):
        pass
        # Request UDP pipeline from server
        # message = {"type": "video", "width": width, "height": height, "duration": duration, "format": "udp"}
        # _json_str = json.dumps(message)
        # self.sock.send(_json_str.encode())
        #
        # # Instantiate VideoStream object
        # vid = VideoStream(duration, src="udp", sink="hls")
        # vid.set_timeout(duration)
        # vid.set_output_resolution(width, height)
        # vid.configure_udp_conn(port=self.media_port)
        # vid.configure_hls(hls_len, hls_maxfiles, hls_duration, hls_root, hls_playloc, hls_loc)
        #
        # # Wait for response from server
        # data = self.sock.recv(1024)
        # if data == b"OK":
        #     self.thread = Thread(target=vid.start_stream)
        #     return True
        # elif data == b"WAIT":
        #     if override:
        #         status = self.send_kill()
        #         if status:
        #             self.thread = Thread(target=vid.start_stream)
        #             return True
        #         else:
        #             return False
        #     else:
        #         print("Server is busy, try again later or override")
        #         return False

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


