import Jetson.networking as jnet

server = jnet.MediaServer(7200)
server.start()