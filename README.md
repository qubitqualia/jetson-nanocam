This Python package provides a simple interface for a CSI camera attached to a Jetson Nano (R32.4.2).  The user can easily configure the `nvarguscamerasrc` and acquire mp4 video
or a series of images separated by a specified time interval.  The package also provides server and client objects that allow for a remote Jetson Nano to send images and videos
to a client PC.  The client PC can be setup to save and display videos and images locally or configured as a HLS sink for forwarding to HTTP clients.

# Camera Setup
The `CSIcamera` class contains all of the properties specified by the Gstreamer element `nvarguscamerasrc`.  It also contains a few custom properties that facilitate use (e.g. 
resolution, framerate, flip-method, captureformat). It should be instantiated and configured prior to connecting it to an `ImageStream` or `VideoStream` object.

```python
from nanocam import tools

cam = tools.CSIcamera()
cam.set_sensorid('0')
cam.set_exposure_time(500000, 100000000)
cam.set_resolution(1920, 1080)
```

# ImageStream on Jetson Nano
The `ImageStream` class can be configured to collect a certain number of frames at a given interval in seconds.  The images can be sent to two 
different sinks: "file" or "opencv".  Note that at present the "opencv" sink has not been tested.

```python
imgstream = tools.ImageStream(3, 5, sink="file")
imgstream.media_path = '/home/media'
imgstream.connect_camera(cam)
imgstream.start_stream()
```
In the example above, the `ImageStream` object has been configured to collect three frames at an interval of five seconds and send the images to
jpg files that will be saved in the specified media path.  The camera used for testing this module was an IMX-219-77 which returned highly 
overexposed images if only one frame was grabbed.  It seems to require 20-30 frames for the camera algorithm to adjust the exposure time to a 
reasonable level.  There may be some way to improve this by tinkering with the camera properties but as a work-around, the `ImageStream` class
is setup to grab 20 frames by default (at max framerate) and only save the last one in the sequence.  This approach seems to work well but also
limits the interval for collecting images to greater than 1 second.  The user must specify a temporary working path for the frames collected by this 
process by setting `imgstream.tmppath`.  This directory is automatically cleaned out after each image has been saved to the media path.

# VideoStream on Jetson Nano
The `VideoStream` class collects video from the CSI camera and sends it to one of four sinks: "file", "opencv", "udp" or "hls".  In most cases, 
the user will want to use the client/server tools discussed below for handling "udp" and "hls" sinks.  As with the `ImageStream` class, the "opencv"
sink has not yet been tested.

```python
vidstream = tools.ImageStream(10, src="camera", sink="file")
vidstream.media_path = '/home/media'
vidstream.connect_camera(cam)
vidstream.start_stream()
```
This example will collect 10 seconds of video and save it as a mp4 file in the media path.

# Client/Server Tools
A remote Jetson Nano with an attached CSI camera can be setup as a server to provide images to a client via file transfer or video via file or 
UDP transfer. 

## Server setup
```python
from nanocam import mediaserver

server = mediaserver.MediaServer(7200)
server.start()
```
This example will setup a media server on a remote Jetson Nano using port 7200 for messaging with clients.  By default, the media transfer port
used for UDP media uses port 5004.

## Client setup 
```python
from nanocam import mediaclient

client = mediaclient.MediaClient()
client.set_msg_port(7200)
client.set_hostip('192.168.1.1')  # IP address of Jetson Nano server
client.set_media_path('/home/media')
client.connect()

# Receive image files from server
# display argument set to True displays images using OpenCV
# override argument set to True will force Jetson Nano server to kill any existing streams to serve this one
# returns tuple of filenames and image array
fname, img_arr = client.image_request(3, 5, width=1920, height=1080, display=True, override=True)

# Receive video from server and save as a file
# src argument can be set to "file" or "udp"
# sink is file on client
# returns tuple of filename and image array
fname, img_arr = client.video_request(10, width=1920, height=1080, display=True, override=True, src="file")

# Receive video from server and send to HLS sink
# Specify hls_root, hls_playloc, hls_loc directories
client.hls_request(10, 'http://localhost/', '/var/www/public/stream0.m3u8', '/var/www/public/fragment%05d.ts', width=1920, height=1080, 
                   override=True, hls_len=10, hls_maxfiles=10, hls_duration=5)
```






