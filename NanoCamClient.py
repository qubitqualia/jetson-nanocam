import socket
import cv2
import uuid
import sys

class MediaClient:
    def __init__(self, host, port):
        self.hostip = host
        self.port = port
        self.media_path = 'C:\\Users\\jmatt\\RemoteMedia\\'
        self.sock = socket.socket()

    def connect(self):
        self.sock.connect((self.hostip, self.port))

    def fetch_image(self, width=3280, height=2464, display=False):

        # Download image from server
        fname = str(uuid.uuid4()) + '.jpg'
        rcvfile = open(self.media_path + fname, 'wb')
        msg = "image@" + str(width) + ',' + str(height)
        self.sock.send(msg.encode())
        print("Downloading image file from server...",)
        _bytes = 0
        while True:
            data = self.sock.recv(1024)
            _bytes += sys.getsizeof(data)
            if data[-4:] == b"DONE":
                print("complete!")
                break
            rcvfile.write(data)
        rcvfile.close()
        print("Received {} bytes from server".format(_bytes))

        # Import image into OpenCV
        img = cv2.imread(self.media_path + fname)

        if display:
            cv2.imshow('image', img)
            cv2.waitKey(0)

        return img

    def fetch_video(self, duration, width=3280, height=2464, display=False):

        # Download video from server
        fname = str(uuid.uuid4()) + '.mp4'
        rcvfile = open(self.media_path + fname, 'wb')
        msg = "video@" + str(width) + ',' + str(height) + '@' + str(duration)
        self.sock.send(msg.encode())
        print("Downloading video file from server...")
        while True:
            data = self.sock.recv(1024)
            if data == b"DONE":
                print("File transfer complete!")
                break
            rcvfile.write(data)
        rcvfile.close()

        # Import video into OpenCV
        vid = cv2.VideoCapture(self.media_path + fname)

        if display:
            while vid.isOpened():
                ret, frame = vid.read()
                cv2.imshow('frame', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            vid.release()
            cv2.destroyAllWindows()

        return vid
