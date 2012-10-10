import sys

import gi
from gi.repository import Clutter
from gi.repository import GdkPixbuf
from gi.repository import Gio

class PixbufTexture(Clutter.Texture):
    """
    Represents a texture that loads its data from a pixbuf.
    """
    __gtype_name__ = 'PixbufTexture'

    def __init__(self, uri=None):
        """
        @type width: int
        @param width: The width to be used for the texture.
        @type height: int
        @param height: The height to be used for the texture.
        @type pixbuf: gdk.pixbuf
        @param pixbuf: A pixbuf from an other widget.
        """
        super(PixbufTexture, self).__init__()

    def realize (self, width, height, pixbuf):
        self.set_width(width)
        self.set_height(height)
        # do we have an alpha value?
        if pixbuf.props.has_alpha:
            bpp = 4
        else:
            bpp = 3

        self.set_from_rgb_data(
            pixbuf.get_pixels(),
            pixbuf.props.has_alpha,
            pixbuf.props.width,
            pixbuf.props.height,
            pixbuf.props.rowstride,
            bpp, 0)
        return self

    @classmethod
    def new_from_uri (cls, uri, cb, args=None):
        inst = cls(uri)
        gfile = Gio.file_new_for_uri(uri)
        return gfile.load_contents_async(None, cls.receive_file, (inst, cb, args))

    @classmethod
    def receive_file (cls, gfile, result, args):
        inst, cb, arg = args
        print "receive_file", args

        try:
            gfile.read_async (1, None, cls.read_complete, args)
        except Exception as exe:
            print exe
            return

    @classmethod
    def read_complete (cls, gfile, result, args):
        inst, cb, arg = args
        print "read_complete", args

        try:
            ins = gfile.read_finish (result)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream (ins, None)
            cb (inst.realize(pixbuf.get_width(), pixbuf.get_height(), pixbuf), arg)
        except gi._glib.GError as exe:
            print exe
            return

if __name__ == '__main__':
    def add_to_stage (texture, stage):
        print "add_to_stage", texture, stage
        stage.add_actor(texture)

    if len(sys.argv) > 1:
        Clutter.init(None)
        stage = Clutter.Stage.get_default()

        PixbufTexture.new_from_uri (sys.argv[1], add_to_stage, stage)

        stage.set_size(500, 500)
        stage.set_color(Clutter.Color.new(0,255,0,0))
        stage.show_all()
        stage.connect('destroy', Clutter.main_quit)
        Clutter.main()
    else:
        print "Provide the full path to the image to load"
