import gi
import numpy
import time
import os
import sys
import uuid
from datetime import datetime

gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst



class StreamBus:
    KILL_THREAD = False


class GstBackEnd:
    def __init__(self):
        self.loop = None
        self.pipeline = None
        self.bus = None
        self.cycles = 0

    def init(self):
        if self.cycles == 0:
            Gst.init(sys.argv)

        GObject.threads_init()
        self.loop = GObject.MainLoop()
        self.pipeline = Gst.Pipeline()
        self.bus = self.pipeline.get_bus()
        self.bus.add_watch(0, self.bus_call, self.loop)

    def quit(self):
        self.pipeline.send_event(Gst.Event.new_eos())

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        print("Starting pipeline")
        try:

            self.loop.run()

        except Exception as e:

            print(e)

        # Cleanup
        self.pipeline.set_state(Gst.State.NULL)
        self.loop = None
        self.pipeline = None
        self.bus = None
        self.cycles += 1

    def bus_call(self, bus, msg, *args):

        if StreamBus.KILL_THREAD:
            print("INSIDE BUS")
            self.pipeline.send_event(Gst.Event.new_eos())
            self.loop.quit()

            return

        if msg.type == Gst.MessageType.EOS:

            print("End-of-stream")
            self.pipeline.send_event(Gst.Event.new_eos())
            self.loop.quit()

            return

        elif msg.type == Gst.MessageType.ERROR:

            print("GST ERROR", msg.parse_error())

            self.loop.quit()

            return

        #elif msg.type == Gst.MessageType.STATE_CHANGED:
        #    if isinstance(msg.src, Gst.Pipeline):
        #        old_state, new_state, pending_state = msg.parse_state_changed()
        #        print("Pipeline state changed from {} to {}.".format(old_state.value_nick, new_state.value_nick))

        #elif msg.type == Gst.MessageType.ELEMENT:
        #    print("UDP packets stopped...closing pipeline")
        #    self.pipeline.send_event(Gst.Event.new_eos())
        #    self.loop.quit()

        #else:
            #print("Unexpected bus message received: {}".format(msg.type))

        return True


class Camera:
    NVCAM_WB_MODE_OFF = 0
    NVCAM_WB_MODE_AUTO = 1
    NVCAM_WB_MODE_INCANDESCENT = 2
    NVCAM_WB_MODE_FLUORESCENT = 3
    NVCAM_WB_MODE_WARM_FLUORESCENT = 4
    NVCAM_WB_MODE_DAYLIGHT = 5
    NVCAM_WB_MODE_CLOUDY_DAYLIGHT = 6
    NVCAM_WB_MODE_TWILIGHT = 7
    NVCAM_WB_MODE_SHADE = 8
    NVCAM_WB_MODE_MANUAL = 9

    NVCAM_NR_OFF = 0
    NVCAM_NR_FAST = 1
    NVCAM_NR_HIGHQUALITY = 2

    NVCAM_EE_OFF = 0
    NVCAM_EE_FAST = 1
    NVCAM_EE_HIGHQUALITY = 2

    NVCAM_AEANTIBANDING_OFF = 0
    NVCAM_AEANTIBANDING_AUTO = 1
    NVCAM_AEANTIBANDING_50HZ = 2
    NVCAM_AEANTIBANDING_60HZ = 3

    ENCODER_OMXH264 = 0
    ENCODER_OMXH265 = 1
    ENCODER_OMXVP8 = 2
    ENCODER_OMXVP9 = 3
    ENCODER_NVV4L2H264 = 4
    ENCODER_NVV4L2H265 = 5
    ENCODER_NVV4L2VP8 = 6
    ENCODER_NVV4L2VP9 = 7


class CSIcamera:
    def __init__(self):
        # nvarguscamera properties
        self.cam_props = []
        self.cam_props.append({"label": "name", "val": None})
        self.cam_props.append({"label": "parent", "val": None})
        self.cam_props.append({"label": "blocksize", "val": None})
        self.cam_props.append({"label": "num-buffers", "val": None})
        self.cam_props.append({"label": "do-timestamp", "val": None})
        self.cam_props.append({"label": "silent", "val": None})
        self.cam_props.append({"label": "timeout", "val": None})
        self.cam_props.append({"label": "wbmode", "val": None})
        self.cam_props.append({"label": "saturation", "val": None})
        self.cam_props.append({"label": "sensor-id", "val": None})
        self.cam_props.append({"label": "exposuretimerange", "val": None})
        self.cam_props.append({"label": "gainrange", "val": None})
        self.cam_props.append({"label": "ispdigitalgainrange", "val": None})
        self.cam_props.append({"label": "tnr-strength", "val": None})
        self.cam_props.append({"label": "tnr-mode", "val": None})
        self.cam_props.append({"label": "ee-mode", "val": None})
        self.cam_props.append({"label": "ee-strength", "val": None})
        self.cam_props.append({"label": "aeantibanding", "val": None})
        self.cam_props.append({"label": "exposurecompensation", "val": None})
        self.cam_props.append({"label": "aelock", "val": None})
        self.cam_props.append({"label": "awblock", "val": None})
        self.cam_props.append({"label": "maxperf", "val": None})
        self.cam_props.append({"custom": "resolution", "val": None})
        self.cam_props.append({"custom": "framerate", "val": None})
        self.cam_props.append({"custom": "flip-method", "val": None})
        self.cam_props.append({"custom": "captureformat", "val": None})


    def get_index(self, key):
        for i, _dict in enumerate(self.cam_props):
            if "label" in _dict:
                if _dict["label"] == key:
                    return i

        return -1

    def get_custom_index(self, key):
        for i, _dict in enumerate(self.cam_props):
            if "custom" in _dict:
                if _dict["custom"] == key:
                    return i

        return -1

    def set_resolution(self, width, height):
        idx = self.get_custom_index("resolution")
        self.cam_props[idx]["val"] = [width, height]

    def get_resolution(self):
        idx = self.get_custom_index("resolution")
        return self.cam_props[idx]["val"]

    def set_framerate(self, frate):
        idx = self.get_custom_index("framerate")
        self.cam_props[idx]["val"] = frate

    def get_framerate(self):
        idx = self.get_custom_index("framerate")
        return self.cam_props[idx]["val"]

    def set_flip_method(self, flip):
        idx = self.get_custom_index("flip-method")
        self.cam_props[idx]["val"] = flip

    def get_flip_method(self):
        idx = self.get_custom_index("flip-method")
        return self.cam_props[idx]["val"]

    def set_capture_format(self, format):
        idx = self.get_custom_index("captureformat")
        self.cam_props[idx]["val"] = format

    def get_capture_format(self):
        idx = self.get_custom_index("captureformat")
        return self.cam_props[idx]["val"]


    # Name of the camera object
    # String. Default: "nvarguscamerasrc0"
    def set_name(self, name):
        idx = self.get_index("name")
        self.cam_props[idx]["val"] = name

    # Parent of the object
    # Object of type "GstObject"
    def set_parent(self, parent):
        idx = self.get_index("parent")
        self.cam_props[idx]["val"] = parent

    # Size in bytes to read per buffer (-1 = default)
    # Unsigned integer. Range 0 - 4294967295 Default: 4096
    def set_blocksize(self, size):
        idx = self.get_index("blocksize")
        self.cam_props[idx]["val"] = size

    # Apply current stream time to buffers
    # Boolean. Default: true
    def set_timestamp(self, on):
        idx = self.get_index("do-timestamp")
        if on:
            val = "true"
        else:
            val = "false"
        self.cam_props[idx]["val"] = val

    # Produce verbose output
    # Boolean. Default: true
    def set_silent(self, on):
        idx = self.get_index("silent")
        if on:
            val = "true"
        else:
            val = "false"
        self.cam_props[idx]["val"] = val

    # Timeout to capture in secs (do not specify both timeout and num-buffers)
    # Unsigned integer. Range: 0-2147483647 Default: 0
    def set_timeout(self, time):
        idx = self.get_index("timeout")
        self.cam_props[idx]["val"] = time

    # White balance affects color temperature of photo
    # Enum "GstNvArgusCamWBMode" Default: 1, "auto"
    def set_white_balance(self, wbenum):
        idx = self.get_index("wbmode")
        self.cam_props[idx]["val"] = wbenum

    # Property to adjust saturation value
    # Float. Range: 0-2 Default: 1
    def set_saturation(self, sat):
        idx = self.get_index("saturation")
        self.cam_props[idx]["val"] = sat

    # Set the id of camera sensor to use
    # Integer. Range: 0-255 Default: 0
    def set_sensorid(self, _id):
        idx = self.get_index("sensor-id")
        self.cam_props[idx]["val"] = _id

    # Property to adjust exposure time range in nanoseconds
    # Use string with values of exposure time range (low, high)
    # in that order, to set the property
    # eg: exposuretimerange="34000 358733000"
    # String. Default: null
    def set_exposure_time(self, tlow, thigh):
        idx = self.get_index("exposuretimerange")
        val = str(tlow) + " " + str(thigh)
        self.cam_props[idx]["val"] = val

    # Property to adjust gain range
    # Use string with values of Gain time range (low, high)
    # in that order, to set property
    # eg: gainrange="1 16"
    # String. Default: null
    def set_gain(self, tlow, thigh):
        idx = self.get_index("gainrange")
        val = str(tlow) + " " + str(thigh)
        self.cam_props[idx]["val"] = val

    # Property to adjust digital gain range
    # Use string with values of ISP Digital Gain Range (low, high)
    # in that order, to set property
    # eg: ispdigitalgainrange="1 8"
    # String. Default: null
    def set_isp_gain(self, tlow, thigh):
        idx = self.get_index("ispdigitalgainrange")
        val = str(tlow) + " " + str(thigh)
        self.cam_props[idx]["val"] = val

    # Property to adjust temporal noise reduction strength
    # Float. Range: -1 to 1 Default: -1
    def set_tnr_strength(self, strength):
        idx = self.get_index("tnr-strength")
        self.cam_props[idx]["val"] = strength

    # Property to select temporal noise reduction mode
    # Enum. Default: 1, "NoiseReduction_Fast"
    def set_tnr_mode(self, modeenum):
        idx = self.get_index("tnr-mode")
        self.cam_props[idx]["val"] = modeenum

    # Property to select edge enhancement mode
    # Enum. Default: 1, "EdgeEnhancement_Fast"
    def set_edge_enhance_mode(self, modeenum):
        idx = self.get_index("ee-mode")
        self.cam_props[idx]["val"] = modeenum

    # Property to adjust edge enhancement strength
    # Float. Range: -1 to 1 Default: -1
    def set_edge_enhance_strength(self, strength):
        idx = self.get_index("ee-strength")
        self.cam_props[idx]["val"] = strength

    # Property to set the auto exposure antibanding mode
    # Enum. Default: 1 "AeAntibandingMode_Auto"
    def set_ae_antibanding_mode(self, aeenum):
        idx = self.get_index("aeantibanding")
        self.cam_props[idx]["val"] = aeenum

    # Property to adjust exposure compensation
    # Float. Range: -2 to 2 Default: 0
    def set_exposure_comp(self, comp):
        idx = self.get_index("exposurecompensation")
        self.cam_props[idx]["val"] = comp

    # Set or unset the auto exposure lock
    # Boolean. Default: False
    def set_auto_exposure_lock(self, on):
        idx = self.get_index("aelock")
        if on:
            val = "true"
        else:
            val = "false"
        self.cam_props[idx]["val"] = val

    # Set or unset the auto white balance lock
    # Boolean. Default: False
    def set_auto_white_bal_lock(self, on):
        idx = self.get_index("awblock")
        if on:
            val = "true"
        else:
            val = "false"
        self.cam_props[idx]["val"] = val

    # Set or unset the max performance
    # Boolean. Default: False
    def set_max_performance(self, on):
        idx = self.get_index("maxperf")
        if on:
            val = "true"
        else:
            val = "false"
        self.cam_props[idx]["val"] = val


class VideoStream:
    def __init__(self, duration, src=None, sink=None):
        self.media_path = "/home/justin/media/"
        self.CAMERASRC = False
        self.UDPSRC = False
        self.APPSRC = False
        self.APPSINK = False
        self.UDPSINK = False
        self.FILESINK = False
        self.HLSSINK = False
        self.outfile = ''

        if src is None or src == "udp":
            self.UDPSRC = True
        elif src == "opencv":
            self.APPSRC = True
        elif src == "camera":
            self.CAMERASRC = True

        if sink is None or sink == "udp":
            self.UDPSINK = True
        elif sink == "hls":
            self.HLSSINK = True
        elif sink == "opencv":
            self.APPSINK = True
        elif sink == "file":
            self.FILESINK = True

        self.duration = duration
        self.port = 5004
        self.Gstobj = GstBackEnd()
        self.cycles = 0
        self.output_res = [3280, 2464]
        self.hostip = None
        self.hls_playlist_length = None
        self.hls_max_files = None
        self.hls_target_duration = None
        self.hls_playlist_root = None
        self.hls_playlist_loc = None
        self.hls_loc = None
        self.encoder = None
        self.img_array = []
        self.Gstobj.init()


    def connect_camera(self, cam):
        if not self.CAMERASRC:
            print("Cannot connect camera because object is not configured to use a camera source...ignoring")
        else:
            self.csicam = cam
            self.csicam.set_resolution(3280, 2464)
            self.csicam.set_capture_format("NV12")
            self.csicam.set_framerate(20)
            self.csicam.set_flip_method(2)
            self.csicam.set_timeout(self.duration)

    def set_timeout(self, duration):
        if self.CAMERASRC and self.csicam is not None:
            print("Camera settings updated!")
            self.csicam.set_timeout = duration
        elif self.CAMERASRC and self.csicam is None:
            print("Cannot complete request because a CSIcamera object has not been connected...ignoring")
        else:
            self.duration = duration

    def set_output_resolution(self, width, height):
        self.output_res = [width, height]

    def configure_udp_conn(self, host='', port=5000):
        self.hostip = host
        self.port = port

    def configure_hls(self, length, maxfiles, dur, root, playloc, loc):
        self.hls_playlist_length = length
        self.hls_max_files = maxfiles
        self.hls_target_duration = dur
        self.hls_playlist_root = root
        self.hls_playlist_loc = playloc
        self.hls_loc = loc

    def start_stream(self):

        if self.Gstobj.cycles != 0:
            self.Gstobj.init()
            self.img_array = []

        self.create_elements()
        self.Gstobj.start()
        StreamBus.KILL_THREAD = False
        self.cycles += 1
        print("Completed cleanup")

        if self.APPSINK:
            return self.img_array
        else:
            return [self.outfile]

    def create_elements(self):

        gst_elements = []

        # Setup camera source element if enabled
        if self.CAMERASRC:
            # Create nvarguscamerasrc element
            videosrc = Gst.ElementFactory.make('nvarguscamerasrc', 'src')

            # Set properties for nvarguscamerasrc using linked camera object settings
            for _dict in self.csicam.cam_props:
                if "label" in _dict:
                    label = _dict["label"]
                    val = _dict["val"]

                    # Do not add "num-buffers" property since it will conflict with "timeout" for video
                    if val is not None:
                        if label != "num-buffers":
                            videosrc.set_property(label, val)

            # Create caps for videosrc
            vidcaps = Gst.ElementFactory.make('capsfilter', 'vidcaps')
            res = self.csicam.get_resolution()
            format = self.csicam.get_capture_format()
            rate = self.csicam.get_framerate()
            caps_str = 'video/x-raw(memory:NVMM), width=(int)' + str(res[0]) + ',' + ' height=(int)' + str(res[1]) + \
                       ',' + ' format=(string)' + format + ',' + ' framerate=(fraction)' + str(rate) + '/1'
            print(caps_str)
            vidcaps.set_property('caps', Gst.caps_from_string(caps_str))

            # Create nvvidconv element
            nvidconv = Gst.ElementFactory.make('nvvidconv', 'convert')
            nvidconv.set_property('flip-method', self.csicam.get_flip_method())

            # Create output caps
            outcaps = Gst.ElementFactory.make('capsfilter', 'outcaps')
            caps_str = 'video/x-raw, width=(int)' + str(self.output_res[0]) + ',' + ' height=(int)' + str(self.output_res[1])
            print(caps_str)
            outcaps.set_property('caps', Gst.caps_from_string(caps_str))

            # Add elements to list
            gst_elements.append(videosrc)
            gst_elements.append(vidcaps)
            gst_elements.append(nvidconv)
            gst_elements.append(outcaps)

        # Setup UDP source element if enabled
        elif self.UDPSRC:
            # Create udpsrc element
            udpsrc = Gst.ElementFactory.make('udpsrc', 'udpsrc')

            # Set properties for udpsrc
            udpsrc.set_property('port', self.port)
            #udpsrc.set_property('timeout', 5000000000)
            udpsrc.set_property('caps', Gst.caps_from_string('application/x-rtp, encoding-name=H264, payload=96'))

            # Create caps for udpsrc
            #udpcaps = Gst.ElementFactory.make('capsfilter', 'udpcaps')
            #udpcaps.set_property('caps', Gst.caps_from_string('application/x-rtp, encoding-name=H264, payload=96'))

            # Create remaining elements required for udpsrc
            rtpdepay = Gst.ElementFactory.make('rtph264depay', 'depay')
            parse = Gst.ElementFactory.make('h264parse', 'parse')

            gst_elements.append(udpsrc)
            #gst_elements.append(udpcaps)
            gst_elements.append(rtpdepay)
            gst_elements.append(parse)

        # Configure encoder (only H264 encoders work presently)
        if self.encoder == Camera.ENCODER_OMXH264:
            encoder_str = "omxh264enc"
        elif self.encoder == Camera.ENCODER_OMXH265:
            encoder_str = "omxh265enc"
        elif self.encoder == Camera.ENCODER_OMXVP8:
            encoder_str = "omxvp8enc"
        elif self.encoder == Camera.ENCODER_OMXVP9:
            encoder_str = "omxvp9enc"
        elif self.encoder == Camera.ENCODER_NVV4L2H264:
            encoder_str = "nvv4l2h264enc"
        elif self.encoder == Camera.ENCODER_NVV4L2H265:
            encoder_str = "nvv4l2h265enc"
        elif self.encoder == Camera.ENCODER_NVV4L2VP8:
            encoder_str = "nvv4l2vp8enc"
        elif self.encoder == Camera.ENCODER_NVV4L2VP9:
            encoder_str = "nvv4l2vp9enc"
        elif self.encoder is None:
            encoder_str = "omxh264enc"

        if self.CAMERASRC:
            if self.FILESINK:
                encoder = Gst.ElementFactory.make(encoder_str, 'encoder')
                gst_elements.append(encoder)
            elif self.UDPSINK:
                encoder = Gst.ElementFactory.make(encoder_str, 'encoder')
                encoder_caps = Gst.ElementFactory.make('capsfilter', 'enc_caps')
                encoder_caps.set_property('caps', Gst.caps_from_string('video/x-h264, stream-format=byte-stream'))
                rtppay = Gst.ElementFactory.make('rtph264pay', 'rtp_pay')
                #rtppay.set_property('caps', Gst.caps_from_string('video/x-h264, stream-format=byte-stream'))
                gst_elements.append(encoder)
                gst_elements.append(encoder_caps)
                gst_elements.append(rtppay)

        # Configure mux
        if self.FILESINK:
            mux = Gst.ElementFactory.make('qtmux', 'mux')
            gst_elements.append(mux)

        elif self.HLSSINK:
            mux = Gst.ElementFactory.make('mpegtsmux', 'mux')
            gst_elements.append(mux)

        # Configure sink
        if self.FILESINK:
            sink = Gst.ElementFactory.make('filesink', 'sink')
            self.outfile = self.media_path + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '.mp4'
            sink.set_property('location', self.outfile)

        elif self.APPSINK:
            sink = Gst.ElementFactory.make('appsink', 'sink')
            sink.set_property('emit-signals', True)
            caps2 = Gst.caps_from_string('video/x-raw, format=(string)BGR')
            sink.set_property("caps", caps2)
            sink.connect("new-sample", self.new_buffer, sink)

        elif self.UDPSINK:
            sink = Gst.ElementFactory.make('udpsink', 'sink')
            sink.set_property('host', self.hostip)
            sink.set_property('port', self.port)

        elif self.HLSSINK:
            sink = Gst.ElementFactory.make('hlssink', 'sink')
            sink.set_property('playlist-length', self.hls_playlist_length)
            sink.set_property('max-files', self.hls_max_files)
            sink.set_property('target-duration', self.hls_target_duration)
            sink.set_property('playlist-root', self.hls_playlist_root)
            sink.set_property('playlist-location', self.hls_playlist_loc)
            sink.set_property('location', self.hls_loc)

        gst_elements.append(sink)

        # Add elements to pipeline
        for elem in gst_elements:
            self.Gstobj.pipeline.add(elem)
            print(elem)

        # Link elements
        last = len(gst_elements) - 2
        for i, elem in enumerate(gst_elements):
            if i <= last:
                elem.link(gst_elements[i+1])
            else:
                break

        return

    def new_buffer(self, sink, data):
        sample = sink.emit("pull-sample")
        arr = VideoStream.gst_to_opencv(sample)
        self.img_array.append(arr)
        return Gst.FlowReturn.OK

    @staticmethod
    def gst_to_opencv(self, sample):
        buf = sample.get_buffer()
        caps = sample.get_caps()

        arr = numpy.ndarray(
            (caps.get_structure(0).get_value('height'),
             caps.get_structure(0).get_value('width'), 3),
            buffer=buf.extract_dup(0, buf.get_size()), dtype=numpy.uint8)

        return arr


class ImageStream:
    def __init__(self, frames, interval, sink=None):
        self.APPSINK = False
        self.FILESINK = False
        self.media_path = "/home/justin/media/"
        self.fnames_array = []
        self.outfile = ''

        if sink is None or sink == "opencv":
            self.APPSINK = True
        elif sink == "file":
            self.FILESINK = True

        self.csicam = None
        self.calc_framerate = round(frames/interval)
        self.tmppath = "/home/justin/media/tmp/"
        self.tmpname = "tmp%05d.jpg"
        self.frames = frames
        self.interval = interval
        self.delay_frames = 20
        self.Gstobj = GstBackEnd()
        self.cycles = 0
        self.img_array = []
        self.new_start = 0
        self.tnow = time.time()
        self.tinit = time.time()
        self.output_res = [1920, 1080]
        self.Gstobj.init()

    def connect_camera(self, cam):
        self.csicam = cam

        # If required settings have not already be made on camera, set them here
        if self.csicam.get_resolution() is None:
            self.csicam.set_resolution(3280, 2464)
        if self.csicam.get_capture_format() is None:
            self.csicam.set_capture_format("NV12")
        if self.csicam.get_framerate() is None:
            self.csicam.set_framerate(20)
        if self.csicam.get_flip_method() is None:
            self.csicam.set_flip_method(2)


    def set_output_resolution(self, width, height):
        self.output_res = [width, height]

    def set_output_file(self, fpath):
        if not self.FILESINK:
            print("Object not configured to use a filesink...ignoring")
        else:
            self.outfile = fpath

    def set_frames(self, frames):
        self.frames = frames

    def set_interval(self, interval):
        self.interval = interval

    def start_stream(self):
        self.img_array = []
        if self.cycles != 0:
            self.fnames_array = []

        while True:
            self.tnow = time.time()

            if self.tnow - self.tinit >= self.interval:
                self.tinit = time.time()
                self.Gstobj.init()
                self.create_elements()
                self.Gstobj.start()
                self.extract_image()
                self.cycles += 1
                print("Completed cleanup")

                if self.cycles == self.frames:
                    self.cycles = 0
                    self.new_start += 1
                    if self.APPSINK:
                        return self.img_array
                    elif self.FILESINK:
                        return self.fnames_array

    def extract_image(self):
        fname_base = self.tmpname.split('%')[0]
        fname = self.tmppath + fname_base + '000' + str(self.delay_frames - 1) + '.jpg'
        os.rename(fname, self.fnames_array[-1])
        os.system('rm -rf %s*' % self.tmppath)

        #cap = cv2.VideoCapture(self.tmppath)
        #idx = 0
        #while cap.isOpened():
        #    ret, frame = cap.read()
        #    if idx == self.delay_time - 2:
        #        cv2.imwrite(self.fnames_array[-1], frame)
        #        break
        #    idx += 1
        #cap.release()

    def create_elements(self):

        gst_elements = []

        # Create nvarguscamerasrc element
        videosrc = Gst.ElementFactory.make('nvarguscamerasrc', 'src')

        # Set properties for nvarguscamerasrc using linked camera object settings
        for _dict in self.csicam.cam_props:
            if "label" in _dict:
                label = _dict["label"]
                val = _dict["val"]

                # Override 'num-buffers' to only collect 20 frames
                if label == "num-buffers":
                    videosrc.set_property(label, self.delay_frames)
                elif label != "timeout" and val is not None:
                    videosrc.set_property(label, val)

        # Create caps for videosrc
        vidcaps = Gst.ElementFactory.make('capsfilter', 'vidcaps')
        res = self.csicam.get_resolution()
        format = self.csicam.get_capture_format()
        rate = self.csicam.get_framerate()
        vidcaps.set_property('caps', Gst.caps_from_string('video/x-raw(memory:NVMM), width=(int)' + str(res[0])
                                                          + ',' + ' height=(int)' + str(res[1]) + ',' +
                                                          ' format=(string)' + format + ',' + ' framerate=(fraction)'
                                                          + str(rate) + '/1'))

        # Create nvvidconv element
        nvidconv = Gst.ElementFactory.make('nvvidconv', 'convert')
        nvidconv.set_property('flip-method', self.csicam.get_flip_method())

        # Create output caps
        outcaps = Gst.ElementFactory.make('capsfilter', 'outcaps')
        outcaps.set_property('caps', Gst.caps_from_string('video/x-raw, width=(int)' + str(self.output_res[0]) + ','
                                                          + ' height=(int)' + str(self.output_res[1])))

        # Add elements to list
        gst_elements.append(videosrc)
        gst_elements.append(vidcaps)
        gst_elements.append(nvidconv)
        gst_elements.append(outcaps)


        # Create encoder element
        encoder = Gst.ElementFactory.make('nvjpegenc', 'encoder')
        gst_elements.append(encoder)


        # Create sink
        if self.FILESINK:
            sink = Gst.ElementFactory.make('multifilesink', 'sink')
            self.outfile = self.media_path + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '.jpg'
            self.fnames_array.append(self.outfile)


            sink.set_property('location', self.tmppath + self.tmpname)
            
        elif self.APPSINK:
            sink = Gst.ElementFactory.make('appsink', 'sink')
            sink.set_property('emit-signals', True)
            caps2 = Gst.caps_from_string('video/x-raw, format=(string){BGR, GRAY8}')
            sink.set_property("caps", caps2)
            sink.connect("new-sample", self.new_buffer, sink)

        gst_elements.append(sink)

        # Add elements to pipeline
        for elem in gst_elements:
            self.Gstobj.pipeline.add(elem)

        # Link elements
        last = len(gst_elements) - 2
        for i, elem in enumerate(gst_elements):
            if i <= last:
                print("Linking {} to {}".format(elem, gst_elements[i+1]))
                elem.link(gst_elements[i + 1])
            else:
                break

        return

    def new_buffer(self, sink, data):
        sample = sink.emit("pull-sample")
        arr = ImageStream.gst_to_opencv(sample)
        self.img_array.append(arr)
        return Gst.FlowReturn.OK

    @staticmethod
    def gst_to_opencv(self, sample):
        buf = sample.get_buffer()
        caps = sample.get_caps()

        arr = numpy.ndarray(
            (caps.get_structure(0).get_value('height'),
             caps.get_structure(0).get_value('width'), 3),
            buffer=buf.extract_dup(0, buf.get_size()), dtype=numpy.uint8)

        return arr


