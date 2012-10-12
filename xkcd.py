#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math

import gi
from gi.repository import GLib
from gi.repository import Clutter
from gi.repository import Gio
from gi.repository import GdkPixbuf

import hacks

Clutter.init(None)

# it'd be nice to have a better force model, but for now:
FORCE = 50
# for some reason Clutter is lying to us… well…
ACTOR_SIZE = 2048

smap = {'x':{-1:'e',1:'w'},'y':{1:'n',-1:'s'}}

# if you set this, all magic goes away
DEBUG=0

if DEBUG:
    sky_color = Clutter.Color.new(0,255,0,0)
    earth_color = Clutter.Color.new(255,0,0,0)

    debug_text = Clutter.Text()
    debug_text.set_text ("hello")
    debug_text.set_color (Clutter.Color.new(255,0,0,200))
else:
    sky_color = Clutter.Color.new(255,255,255,0)
    earth_color = Clutter.Color.new(0,0,0,0)

class XaMap:
    def __init__(self, tex=None, stage=None):
        self.current_tile = [0, 0]
        self.cache_dir = os.path.abspath(".cache")
        self.base_url = "http://imgs.xkcd.com/clickdrag/"

        try:
            os.mkdir(self.cache_dir)
        except OSError:
            pass

        self.tile_cache = {}

        if (tex):
            self.tex = tex
        else:
            for i in range (-1, 2):
                for j in range (-1, 2):
                    self.new_tile (i, j)
#            self.tex = ([self.new_col ( 1, 0, 0),
#                         self.new_col ( 0, 0, 0),
#                         self.new_col (-1, 0, 0)])
#            self.tex = ([[None, self.new_tex (1, 0), None],
#                         self.new_col (0, 0, 0),
#                         [None, None, None]])

        print "DEBUG", tex

        if (stage):
            self.stage = stage
        else:
            self.stage = Clutter.Stage.get_default()
        self.stage_size = self.stage.get_size()
        self.stage.set_background_color (sky_color)
        self.stage.set_title ("XKCD: #1110")

        self.scroll = Clutter.Group()
        self.scroll.set_size (-1, -1)

        self.stage.add_actor (self.scroll)
        self.stage.show()
        if DEBUG:
            self.stage.add_actor (debug_text)

        self.scroll.set_position (0, -1100)
        self.stage.connect ("key-press-event", self.on_key_press, self.scroll)

    def remove_tile (self, x, y):
        try:
            print "removing:", (x,y)
            self.scroll.remove_actor (self.tile_cache[x, y])
            del(self.tile_cache[x, y])
        except Exception as exe:
            print "Couldn't remove tile, probably never made it", exe

    def new_col (self, direction, x, y):
        self.new_tile    (x + direction, y + 1)
        self.new_tile    (x + direction, y)
        self.new_tile    (x + direction, y - 1)
        self.remove_tile (x - 2*direction, y + 1)
        self.remove_tile (x - 2*direction, y)
        self.remove_tile (x - 2*direction, y - 1)

    def new_row (self, direction, x, y):
        self.new_tile    (x + 1, y + direction)
        self.new_tile    (x    , y + direction)
        self.new_tile    (x - 1, y + direction)
        self.remove_tile (x + 1, y - 2*direction)
        self.remove_tile (x    , y - 2*direction)
        self.remove_tile (x - 1, y - 2*direction)

    def get_tile_filename (self, x, y):
        if (x<=0):
            x = x - 1
        if (y>=0):
            y = y + 1

        return "%d%c%d%c.png" % (abs(y), smap['y'][y/abs(y)], abs(x), smap['x'][x/abs(x)])

    def new_tile (self, x, y, cb=None):
        if not cb:
            cb = self.show_tile
        f = self.get_tile_filename (x, y)
        uri = self.check_cache (f)
        print "loading tile for position: ", (x, y), "\tusing method", uri
        return hacks.PixbufTexture.new_from_uri (uri, cb, (x,y))

    def check_cache (self, fn):
        try:
            os.stat (self.cache_dir + '/' + fn)
        except OSError:
            return ("http://imgs.xkcd.com/clickdrag/" + fn)

        return 'file://' + self.cache_dir + '/' + fn

    def set_current_tile (self, tile):
        self.current_tile = tile

    def show_tile (self, actor, pos):
        x, y = pos
        #        nx = (-self.current_tile[0] + x)*ACTOR_SIZE
        #        ny = (-self.current_tile[1] + y)*ACTOR_SIZE
        nx = -x*ACTOR_SIZE
        ny = -y*ACTOR_SIZE

        if self.tile_cache.has_key ((x,y)):
            print "Tile already cached at", (x,y), self.tile_cache
            raise KeyError

        self.tile_cache[(x,y)] = actor

        print "moving", actor,  "to:", (x,y), self.current_tile, "to", nx, ny
        if not actor:
            print "No tile at", x, y
            return

        actor.set_position(nx, ny)
        self.scroll.add_actor (actor)

        action = Clutter.DragAction()
#        action.connect ("drag-begin",    self.drag_begin_cb)
        action.connect ("drag-end"  ,    self.drag_end_cb)
        action.connect ("drag-progress", self.drag_progress_cb, self.scroll)
        actor.add_action (action)
        actor.set_reactive (True)

        actor.props.clip_to_allocation = True

    def drag_begin_cb (self, action, actor, event_x, event_y, modifiers):
        print "DRAG START\t", self.scroll.get_position(), event_x, event_y

    def drag_end_cb (self, action, actor, event_x, event_y, modifiers):
         self.recenter ()

    def drag_progress_cb (self, action, actor, delta_x, delta_y, arg=None):
        if arg:
            arg.move_by (delta_x, delta_y)
            return False

    def do_recenter (self, tile, motion):
        print "recentering", tile, motion
        self.set_current_tile(tile)

        if DEBUG:
            debug_text.set_text ("current Tile:" + str(tile) + self.get_tile_filename(*tile))
        if motion[0]:
            print "adding a col"
            self.new_col(motion[0], *tile)
        if motion[1]:
            print "adding a row"
            self.new_row(motion[1], *tile)

    def on_key_press (self, stage, event, actor):
        if event.keyval == Clutter.KEY_q:
            Clutter.main_quit()

        if event.keyval == Clutter.KEY_Up:
            actor.move_by (0, FORCE)

        if event.keyval == Clutter.KEY_Down:
            actor.move_by (0, -FORCE)

        if event.keyval == Clutter.KEY_Left:
            actor.move_by (FORCE, 0)

        if event.keyval == Clutter.KEY_Right:
            actor.move_by (-FORCE, 0)

        self.recenter ()

    def recenter (self):
        pos = self.scroll.get_position()
        tile = [1 + int(math.floor((pos[i] - self.stage_size[i])/ACTOR_SIZE)) for i in range(2)]

        if (pos[1] > 0):
            self.stage.set_background_color (sky_color)
        else:
            self.stage.set_background_color (earth_color)


        print "recenter?", pos, tile, self.current_tile
        if (tile != self.current_tile):
            motion = [tile[i] - self.current_tile[i] for i in range(2)]
            self.do_recenter (tile, motion)

def show_cb (actor, coord):
    x, y = coord
#    print "show:", coord

tex = XaMap()

Clutter.main()
