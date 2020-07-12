import Jetson.networking as jnet
import Jetson.nanocam as nc
from threading import Thread

print("Starting local video thread")
vid = nc.VideoStream(80, src="camera", sink="file")
cam = nc.CSIcamera()
vid.connect_camera(cam)
thread1 = Thread(target=vid.start_stream, args=())
thread1.start()

server = jnet.MediaServer(7200)
server.start()