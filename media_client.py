import Jetson.networking as jnet

client = jnet.MediaClient('192.168.1.168', 7200)
client.connect()

hls_root = "http://192.168.1.88/"
path = "/home/justin/media/hls/"
hls_playloc = path + "stream0.m3u8"
hls_loc = path + "fragment%05d.ts"
status = client.hls_request(20, hls_root, hls_playloc, hls_loc, override=True)
print("FROM MAIN --> Status is {}".format(status))
