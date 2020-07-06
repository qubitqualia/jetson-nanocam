#!/usr/bin/python3

import gi

gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst

print(Gst.version())



def bus_call(bus, msg, *args):
    # print("BUSCALL", msg, msg.type, *args)

    if msg.type == Gst.MessageType.EOS:

        print("End-of-stream")
        pipeline.send_event(Gst.Event.new_eos())
        loop.quit()


        return

    elif msg.type == Gst.MessageType.ERROR:

        print("GST ERROR", msg.parse_error())

        loop.quit()

        return

    return True








if __name__ == "__main__":

    GObject.threads_init()

    # initialization

    loop = GObject.MainLoop()

    Gst.init(None)

    # create elements

    pipeline = Gst.Pipeline()

    # watch for messages on the pipeline's bus (note that this will only

    # work like this when a GLib main loop is running)

    bus = pipeline.get_bus()

    bus.add_watch(0, bus_call, loop)  # 0 == GLib.PRIORITY_DEFAULT

    # create elements

    videosrc = Gst.ElementFactory.make('nvarguscamerasrc', "src")

    # videosrc = Gst.ElementFactory.make('rpicamsrc', "src0")

    videosrc.set_property("num-buffers", 30)

    caps_convert_src = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
    caps_convert_src.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)3280, height=(int)2464, format=(string)NV12, framerate=(fraction)20/1"))

    convert = Gst.ElementFactory.make("nvvidconv", "convert")
    convert.set_property("flip-method", 2)

    encode = Gst.ElementFactory.make("omxh264enc", "encode")

    mux = Gst.ElementFactory.make("qtmux", "mux")

    sink = Gst.ElementFactory.make("filesink", 'sink')

    sink.set_property("location", 'new_vid_out5.mp4')

    # add elements

    pipeline.add(videosrc)

    pipeline.add(caps_convert_src)

    pipeline.add(convert)

    pipeline.add(encode)

    pipeline.add(mux)

    pipeline.add(sink)

    # link elements
    videosrc.link(convert)
    convert.link(caps_convert_src)
    # srcpad = caps_convert_src.get_static_pad("src")
    caps_convert_src.link(encode)
    encode.link(mux)
    mux.link(sink)

    # run

    pipeline.set_state(Gst.State.PLAYING)

    try:

        loop.run()

    except Exception as e:

        print(e)

    # cleanup

    pipeline.set_state(Gst.State.NULL)

