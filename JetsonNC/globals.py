
class StreamStatus:
    LOCAL_BUSY = False
    LOCAL_KILL = False


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