from nanocam import mediaclient

client = mediaclient.MediaClient()
client.set_hostip('192.168.1.168')
client.set_msg_port(7155)
client.connect()

client.image_request(5, 1, display=True)

