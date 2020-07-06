#!/usr/bin/python3

import gi
import monitor_service
import time

gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst

class Enum:
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

class GstBackEnd:
    def __init__(self):
        self.loop = None
        self.pipeline = None
        self.bus = None
        self.cycles = 0

    def init(self):
        if self.cycles == 0:
            Gst.init(None)

        GObject.threads_init()
        self.loop = GObject.MainLoop()
        self.pipeline = Gst.Pipeline()
        self.bus = self.pipeline.get_bus()
        self.bus.add_watch(0, self.bus_call, self.loop)

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)
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

        print("Completed cleanup")

    def bus_call(self, bus, msg, *args):
        if msg.type == Gst.MessageType.EOS:

            print("End-of-stream")
            self.pipeline.send_event(Gst.Event.new_eos())
            self.loop.quit()

            return

        elif msg.type == Gst.MessageType.ERROR:

            print("GST ERROR", msg.parse_error())

            self.loop.quit()

            return

        return True



class UDPStreamOut:
    def __init__(self, csicam, host, port, res=None, framerate=None):
        self.csicam = csicam
        self.hostip = host
        self.mediaport = port
        self.Gstobj = GstBackEnd()

        if res is None:
            self.resolution = [3280, 2564]
        else:
            self.resolution = res

        if framerate is None:
            self.framerate = 21
        else:
            self.framerate = framerate

    def start(self):
        if self.Gstobj.cycles != 0:
            self.Gstobj.init()
            self.create_elements()

        self.Gstobj.pipeline.set_state(Gst.State.PLAYING)
        try:

            self.Gstobj.loop.run()

        except Exception as e:

            print(e)

        # Cleanup
        self.Gstobj.pipeline.set_state(Gst.State.NULL)
        self.Gstobj.loop = None
        self.Gstobj.pipeline = None
        self.Gstobj.bus = None
        self.Gstobj.cycles += 1
        self.cycles += 1

        print("Completed cleanup")

    def create_elements(self):

        # CSI camera source
        videosrc = Gst.ElementFactory.make('nvarguscamerasrc', "src")

        for _dict in self.csicam.cam_props:
            if _dict["val"] is not None:
                label = _dict["label"]
                val = _dict["val"]
                videosrc.set_property(label, val)

        # Caps filter for CSI <--> nvvidconv
        caps_convert_src = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
        caps_convert_src.set_property('caps', Gst.Caps.from_string(
            "video/x-raw(memory:NVMM), width=(int)" + str(self.resolution[0]) + " , height=(int)" +
            str(self.resolution[1]) + " , format=(string)NV12, framerate=(fraction)" +
            str(self.framerate) + "/1"))

        # Convert element
        convert = Gst.ElementFactory.make("nvvidconv", "convert")
        convert.set_property("flip-method", 2)

        # Encoder element
        encode = Gst.ElementFactory.make("omxh264enc", "encode")

        # Mux element
        mux = Gst.ElementFactory.make("qtmux", "mux")

        # UDP sink element
        sink = Gst.ElementFactory.make("udpsink", 'sink')
        sink_split = self.outfile.split('.')
        sink_str = sink_split[0] + str(self.cycles) + '.' + sink_split[1]
        sink.set_property("location", sink_str)

        # Add elements

        self.Gstobj.pipeline.add(videosrc)
        self.Gstobj.pipeline.add(caps_convert_src)
        self.Gstobj.pipeline.add(convert)
        self.Gstobj.pipeline.add(encode)
        self.Gstobj.pipeline.add(mux)
        self.Gstobj.pipeline.add(sink)

        # Link elements
        videosrc.link(convert)
        convert.link(caps_convert_src)
        caps_convert_src.link(encode)
        encode.link(mux)
        mux.link(sink)

        return


class FileStream:
    def __init__(self, csicam, outfile, encoder=None):
        self.csicam = csicam
        self.outfile = outfile
        self.encoder = encoder      #enum
        self.Gstobj = GstBackEnd()
        self.cycles = 0
        self.resolution = None
        self.framerate = None
        self.flip_method = None
        self.capture_format = None
        self.Gstobj.init()
        self.create_elements()

    def start(self):
        if self.Gstobj.cycles != 0:
            self.Gstobj.init()
            self.create_elements()

        self.Gstobj.pipeline.set_state(Gst.State.PLAYING)
        try:

            self.Gstobj.loop.run()

        except Exception as e:

            print(e)

        # Cleanup
        self.Gstobj.pipeline.set_state(Gst.State.NULL)
        self.Gstobj.loop = None
        self.Gstobj.pipeline = None
        self.Gstobj.bus = None
        self.Gstobj.cycles += 1
        self.cycles += 1

        print("Completed cleanup")


    def create_elements(self):

        self.resolution = self.csicam.get_resolution()
        if self.resolution is None:
            self.resolution = [3280, 2464]

        self.framerate = self.csicam.get_framerate()
        if self.framerate is None:
            self.framerate = 20

        self.capture_format = self.csicam.get_capture_format()
        if self.capture_format is None:
            self.capture_format = "NV12"

        self.flip_method = self.csicam.get_flip_method()
        if self.flip_method is None:
            self.flip_method = 0

        # CSI camera source
        videosrc = Gst.ElementFactory.make('nvarguscamerasrc', "src")

        for _dict in self.csicam.cam_props:
            if "label" in _dict:
                if _dict["val"] is not None:
                    label = _dict["label"]
                    val = _dict["val"]
                    videosrc.set_property(label, val)

        # Caps filter for CSI <--> nvvidconv
        caps_convert_src = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
        caps_convert_src.set_property('caps', Gst.Caps.from_string(
            "video/x-raw(memory:NVMM), width=(int)" + str(self.resolution[0]) + " , height=(int)" +
            str(self.resolution[1]) + " , format=(string)" + self.capture_format + ", framerate=(fraction)" +
            str(self.framerate) + "/1"))

        # Convert element
        convert = Gst.ElementFactory.make("nvvidconv", "convert")
        convert.set_property("flip-method", self.flip_method)

        # Encoder element
        if self.encoder == Enum.ENCODER_OMXH264:
            encoder_str = "omxh264enc"
        elif self.encoder == Enum.ENCODER_OMXH265:
            encoder_str = "omxh265enc"
        elif self.encoder == Enum.ENCODER_OMXVP8:
            encoder_str = "omxvp8enc"
        elif self.encoder == Enum.ENCODER_OMXVP9:
            encoder_str = "omxvp9enc"
        elif self.encoder == Enum.ENCODER_NVV4L2H264:
            encoder_str = "nvv4l2h264enc"
        elif self.encoder == Enum. ENCODER_NVV4L2H265:
            encoder_str = "nvv4l2h265enc"
        elif self.encoder == Enum.ENCODER_NVV4L2VP8:
            encoder_str = "nvv4l2vp8enc"
        elif self.encoder == Enum.ENCODER_NVV4L2VP9:
            encoder_str = "nvv4l2vp9enc"
        elif self.encoder is None:
            encoder_str = "omxh264enc"

        encode = Gst.ElementFactory.make(encoder_str, "encode")

        # Mux element
        mux = Gst.ElementFactory.make("qtmux", "mux")

        # Filesink element
        sink = Gst.ElementFactory.make("filesink", 'sink')
        sink_split = self.outfile.split('.')
        sink_str = sink_split[0] + str(self.cycles) + '.' + sink_split[1]
        sink.set_property("location", sink_str)

        # Add elements

        self.Gstobj.pipeline.add(videosrc)
        self.Gstobj.pipeline.add(caps_convert_src)
        self.Gstobj.pipeline.add(convert)
        self.Gstobj.pipeline.add(encode)
        self.Gstobj.pipeline.add(mux)
        self.Gstobj.pipeline.add(sink)

        # Link elements
        videosrc.link(convert)
        convert.link(caps_convert_src)
        caps_convert_src.link(encode)
        encode.link(mux)
        mux.link(sink)

        return


