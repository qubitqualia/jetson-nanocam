from NanoCamClient import MediaClient
import imutils
import cv2

client = MediaClient('192.168.1.168', 7200)
client.connect()

# Image test
img = client.fetch_image(display=False)
img = imutils.resize(img, width=640, height=480)
cv2.imshow('image', img)
cv2.waitKey(0)

# Video test
# vid = client.fetch_video(4, display=True)