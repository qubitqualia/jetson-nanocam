import Jetson.mediaclient as jnet

client = jnet.MediaClient('192.168.1.168', 7200)
client.connect()

# ***WORKS***
#print("Requesting images from server...")
#fname, img_arr = client.image_request(3, 5, display=True)

#print("File names downloaded: {}".format(fname))

# ***WORKS***
#print("Requesting video from server...")
#fname, img_arr = client.video_request(5, display=True)\

# ***WORKS***
#fname, img_arr = client.video_request(5, src="udp")

